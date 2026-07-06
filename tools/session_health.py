#!/usr/bin/env python3
"""
セッション容量・健康診断ツール（v2: 実コンテキスト方式・2026-06-13改修）

現在のClaude Codeセッション（jsonl）を分析し、健康状態をチェックする。
Stop hookから呼ばれて、警告閾値を超えたときだけ画面に出力する。

🔴 v2の本質（戻すな）：
  旧方式は「ファイル累計サイズ・累計入力回数」で判定していたが、これは
  /compact（圧縮）後も減らない累計値のため誤報の温床だった（実例：9.8MBの
  ファイルでも圧縮済みで実コンテキストは6.8万tokens＝健康体）。
  v2は jsonl 内の assistant usage（input + cache_read + cache_creation）から
  「いまコンテキストに載っている実トークン量」を読み、モデルの窓サイズに
  対する使用率で判定する。これが唯一正確な容量指標。

判定ロジック：
  コンテキスト使用率: WARN=70%, CRIT=85%（自動圧縮は約95%で強制発動）
  画像（現コンテキスト内）: WARN=25, CRIT=40（圧縮で消えた分は数えない）
  累計サイズ・累計入力回数: 参考表示のみ（判定には使わない）

使い方：
  python3 tools/session_health.py            # 自動検出した最新セッションを診断
  python3 tools/session_health.py --quiet    # OK時は無出力（Stop hook向け）
  python3 tools/session_health.py --json     # JSON出力
  python3 tools/session_health.py --session /path/to/xxxxx.jsonl
  python3 tools/session_health.py --window 200000   # 窓サイズを手動指定
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # my-ai-company/

# 閾値（v2: コンテキスト使用率ベース）
THRESHOLDS = {
    "context_pct": {"warn": 70, "crit": 85},   # 窓に対する使用率%
    "images": {"warn": 25, "crit": 40},        # 現コンテキスト内の画像数
}

# 旧方式フォールバック用（usage情報が取れない異常時のみ）
LEGACY_THRESHOLDS = {
    "size_mb": {"warn": 5, "crit": 9},
    "turns": {"warn": 30, "crit": 50},
}

# モデル→コンテキスト窓サイズ（tokens）
# 根拠: 2026-05-03 claude-opus-4-7 が967,345tokensで自動圧縮（auto）＝窓100万。
#       claude-opus-4-8 は457k到達でも自動圧縮なし＝窓>457k。
MODEL_WINDOWS = [
    ("claude-opus-4", 1_000_000),
    ("claude-fable", 1_000_000),
    ("claude-sonnet-4", 200_000),
    ("claude-haiku", 200_000),
]
DEFAULT_WINDOW = 200_000
STANDARD_WINDOWS = [200_000, 500_000, 1_000_000]


def session_from_hook_stdin() -> tuple[Path | None, bool]:
    """Claude Codeがhookのstdinに渡すJSONから現在セッションの正確なパスを取得。

    hookは {"session_id":..., "transcript_path":..., ...} をstdinに渡す。
    これが「現在のセッション」の唯一正確な情報源。

    戻り値: (jsonlパス, hook起動か)
      - (Path, True)  : transcript_path が指すファイルが実在 → そのまま診断
      - (None, True)  : hookは起動したが現セッションのjsonlがまだ無い/読めない
                        ＝引き継ぎ直後など「中身ゼロの新セッション」。
                        ⚠️ ここで mtime推測に逃げると前セッションの巨大ファイルを
                        誤検出してCRIT表示になる（2026-06-02再発・修正）。よって
                        呼び出し側は推測せず「健康（新品）」扱いにすること。
      - (None, False) : stdinが空＝端末からの手動実行 → mtime推測フォールバック可。
    """
    import select
    try:
        # stdinに即読めるデータがある時だけ読む（TTYならタイムアウト0で空＝手動実行）
        if not select.select([sys.stdin], [], [], 0.0)[0]:
            return None, False
        raw = sys.stdin.read()
        if not raw.strip():
            return None, False
        d = json.loads(raw)
        tp = d.get("transcript_path") or d.get("transcriptPath")
        if tp:
            p = Path(tp).expanduser()
            if p.exists():
                return p, True
        # hookは起動したが transcript が未作成/読めない＝新セッション
        return None, True
    except Exception:
        # stdinはあったがJSON壊れ等。安全側に倒して「hook起動・対象不明」扱い
        return None, True


def find_current_session() -> Path | None:
    """フォールバック：現プロジェクトの最新セッションjsonlを推定。

    ⚠️ これは推測（mtime順）であり、hookのtranscript_pathが取れない場合の
    最終手段。新セッション起動直後は自分のファイルが空で、前セッションの
    大きいファイルを誤検出しうる（だからhook stdinを優先する）。
    """
    cwd = Path.cwd().resolve()
    encoded = "-" + str(cwd).replace("/", "-").lstrip("-")
    base = Path.home() / ".claude" / "projects" / encoded
    if not base.exists():
        encoded = "-" + str(PROJECT_ROOT).replace("/", "-").lstrip("-")
        base = Path.home() / ".claude" / "projects" / encoded
        if not base.exists():
            return None

    sessions = sorted(
        base.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return sessions[0] if sessions else None


def _is_real_user_message(content) -> bool:
    """tool_result ではない、ユーザーが実際に入力したメッセージか判定。"""
    if isinstance(content, str):
        return True
    if not isinstance(content, list):
        return False
    for item in content:
        if isinstance(item, dict):
            t = item.get("type")
            if t == "tool_result":
                return False
            if t in ("text", "image"):
                return True
    return False


def _usage_total(usage: dict) -> int:
    """assistant usageから「その時点のコンテキスト総量」を計算。"""
    return (usage.get("input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0))


def _count_images(obj) -> int:
    n = 0
    if isinstance(obj, dict):
        if obj.get("type") == "image":
            n += 1
        for v in obj.values():
            n += _count_images(v)
    elif isinstance(obj, list):
        for item in obj:
            n += _count_images(item)
    return n


def analyze_session(jsonl_path: Path) -> dict:
    """セッションjsonlを解析して指標を返す。

    v2: 圧縮境界（compact_boundary）を認識し、
      - context_tokens: 最新assistant usageによる現在のコンテキスト量
      - images_in_context / turns_since_compact: 最後の圧縮以降のみカウント
      - compacts: 圧縮履歴（trigger, preTokens, postTokens実測）
    を返す。旧指標（累計）も参考値として残す。
    """
    file_size = jsonl_path.stat().st_size

    # 累計（参考値・旧指標）
    total_images = 0
    total_user_turns = 0
    assistant_turns = 0
    # 現コンテキスト（圧縮後のみ）
    images_in_context = 0
    turns_since_compact = 0
    context_tokens = 0
    model = None
    compacts: list[dict] = []  # {trigger, preTokens, postTokens}
    pending_post = False  # 圧縮直後の最初のusageをpostTokensとして記録する

    last_assistant_id = None
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("isSidechain"):
                continue  # subagent等の脇道はコンテキスト外
            if d.get("subtype") == "compact_boundary":
                meta = d.get("compactMetadata", {}) or {}
                compacts.append({
                    "trigger": meta.get("trigger"),
                    "preTokens": meta.get("preTokens"),
                    "postTokens": None,
                })
                pending_post = True
                # 圧縮で現コンテキストの画像・ターンはリセットされる
                images_in_context = 0
                turns_since_compact = 0
                continue
            msg = d.get("message", d)
            role = msg.get("role") if isinstance(msg, dict) else None
            content = msg.get("content") if isinstance(msg, dict) else None
            if role == "user" and _is_real_user_message(content):
                if not d.get("isCompactSummary"):  # 圧縮要約はユーザー入力ではない
                    total_user_turns += 1
                    turns_since_compact += 1
            elif role == "assistant":
                msg_id = msg.get("id") or d.get("uuid") or d.get("timestamp")
                if msg_id != last_assistant_id:
                    assistant_turns += 1
                    last_assistant_id = msg_id
                usage = msg.get("usage")
                if usage:
                    tot = _usage_total(usage)
                    if tot > 0:
                        context_tokens = tot
                        if msg.get("model"):
                            model = msg["model"]
                        if pending_post and compacts:
                            compacts[-1]["postTokens"] = tot
                            pending_post = False
            n_img = _count_images(msg)
            total_images += n_img
            images_in_context += n_img

    return {
        "session_file": str(jsonl_path),
        # --- v2主指標 ---
        "context_tokens": context_tokens,
        "model": model,
        "images_in_context": images_in_context,
        "turns_since_compact": turns_since_compact,
        "compacts": compacts,
        # --- 参考（旧指標・累計）---
        "size_bytes": file_size,
        "size_mb": round(file_size / 1024 / 1024, 2),
        "image_count": total_images,
        "user_turns": total_user_turns,
        "assistant_turns": assistant_turns,
        "total_turns": total_user_turns + assistant_turns,
    }


def resolve_window(metrics: dict, override: int | None = None) -> tuple[int, str]:
    """コンテキスト窓サイズを決定。優先順: 引数/環境変数 > セッション内証拠 > モデル表。"""
    if override:
        return override, "手動指定"
    env = os.environ.get("SESSION_WINDOW_TOKENS")
    if env and env.isdigit():
        return int(env), "環境変数"
    # 証拠: 自動圧縮(auto)のpreTokensは窓の約95%で発動する
    auto_pres = [c["preTokens"] for c in metrics.get("compacts", [])
                 if c.get("trigger") == "auto" and c.get("preTokens")]
    evidence = max(auto_pres) if auto_pres else 0
    # 現在の実測コンテキストも下限の証拠になる
    evidence = max(evidence, metrics.get("context_tokens", 0))
    model = metrics.get("model") or ""
    model_window = DEFAULT_WINDOW
    for prefix, w in MODEL_WINDOWS:
        if model.startswith(prefix):
            model_window = w
            break
    if evidence > model_window:
        # 実測がモデル表を超えている → 実測を包含する標準サイズに引き上げ
        for w in STANDARD_WINDOWS:
            if evidence <= w * 0.97:
                return w, "セッション内実測から推定"
        return STANDARD_WINDOWS[-1], "セッション内実測から推定"
    return model_window, f"モデル表({model or '不明'})"


def estimate_compact_effect(metrics: dict, window: int) -> dict:
    """圧縮（/compact）した場合の効果と、残り余地を見積もる。"""
    ctx = metrics["context_tokens"]
    crit_tokens = int(window * THRESHOLDS["context_pct"]["crit"] / 100)

    # 圧縮後のコンテキスト量: このセッション自身の実績 > 全社実績(約5%・最低3万)
    own_posts = [c["postTokens"] for c in metrics.get("compacts", []) if c.get("postTokens")]
    if own_posts:
        est_post = own_posts[-1]
    else:
        est_post = max(30_000, int(ctx * 0.05))
    est_post = min(est_post, ctx)  # 現在より大きくはならない

    # このセッションの「1入力あたり平均消費」: 圧縮後の基準点からの増分で計算
    base = own_posts[-1] if own_posts else 25_000  # 初期読込(CLAUDE.md等)ぶん
    turns = max(metrics.get("turns_since_compact", 0), 1)
    avg_per_turn = max((ctx - base) / turns, 2_000)

    remaining_now = max(int((crit_tokens - ctx) / avg_per_turn), 0)
    remaining_after = max(int((crit_tokens - est_post) / avg_per_turn), 0)

    return {
        "est_post_tokens": int(est_post),
        "est_post_pct": round(est_post / window * 100, 1),
        "freed_tokens": max(int(ctx - est_post), 0),
        "avg_tokens_per_turn": int(avg_per_turn),
        "remaining_turns_now": remaining_now,
        "remaining_turns_after_compact": remaining_after,
    }


def evaluate(metrics: dict, window: int | None = None) -> dict:
    """指標を閾値で評価。v2: コンテキスト使用率＋コンテキスト内画像で判定。"""
    if window is None:
        window, _ = resolve_window(metrics)

    levels = {}
    if metrics.get("context_tokens"):
        pct = metrics["context_tokens"] / window * 100
        metrics["context_pct"] = round(pct, 1)
        metrics["window_tokens"] = window
        t = THRESHOLDS["context_pct"]
        levels["context"] = "CRIT" if pct >= t["crit"] else "WARN" if pct >= t["warn"] else "OK"
        t = THRESHOLDS["images"]
        v = metrics["images_in_context"]
        levels["images"] = "CRIT" if v >= t["crit"] else "WARN" if v >= t["warn"] else "OK"
        metrics["judge_mode"] = "v2(実コンテキスト)"
    else:
        # usage情報なし＝異常系。旧方式（累計）にフォールバック
        for key, value in [("size_mb", metrics["size_mb"]), ("turns", metrics["user_turns"])]:
            t = LEGACY_THRESHOLDS[key]
            levels[key] = "CRIT" if value >= t["crit"] else "WARN" if value >= t["warn"] else "OK"
        metrics["judge_mode"] = "legacy(累計・参考値)"

    if "CRIT" in levels.values():
        overall = "CRIT"
    elif "WARN" in levels.values():
        overall = "WARN"
    else:
        overall = "OK"
    return {"levels": levels, "overall": overall}


def format_report(metrics: dict, evaluation: dict) -> str:
    """人間向けレポート文字列を生成。"""
    overall = evaluation["overall"]
    icon = {"OK": "✅", "WARN": "⚠️ ", "CRIT": "🚨"}[overall]
    lines = [f"\n{icon} セッション健康診断: {overall}"]

    if metrics.get("context_tokens"):
        window = metrics["window_tokens"]
        pct = metrics["context_pct"]
        t = THRESHOLDS["context_pct"]
        lines.append(
            f"   🧠 コンテキスト: {metrics['context_tokens']:,} / {window:,} tokens"
            f" = {pct}% [{evaluation['levels']['context']}]"
            f"  (warn≧{t['warn']}%, crit≧{t['crit']}%)"
        )
        ti = THRESHOLDS["images"]
        lines.append(
            f"   🖼️  画像(現コンテキスト内): {metrics['images_in_context']:>3} 枚"
            f" [{evaluation['levels']['images']}]  (warn≧{ti['warn']}枚, crit≧{ti['crit']}枚)"
        )
        n_compact = len(metrics.get("compacts", []))
        lines.append(
            f"   📚 参考(累計・判定外): {metrics['size_mb']}MB / 画像{metrics['image_count']}枚"
            f" / 入力{metrics['user_turns']}回 / 圧縮{n_compact}回実施済み"
        )

        if overall in ("WARN", "CRIT"):
            est = estimate_compact_effect(metrics, window)
            head = "🚨 危険ゾーン: 作業を続ける前にどちらか選んでください" if overall == "CRIT" \
                else "👉 容量が増えてきました。対応の選択肢（効果の見積り付き）:"
            lines.append("")
            lines.append(head)
            lines.append(
                f"   A) `/compact` で圧縮 → 推定 {pct}% → {est['est_post_pct']}%"
                f"（約{est['freed_tokens'] // 10000}万tokens解放・画像も除去）。"
                f"圧縮後はあと約{est['remaining_turns_after_compact']}回の入力が可能"
                f"（このセッションの平均ペース {est['avg_tokens_per_turn']:,}tokens/回で換算）"
            )
            lines.append(
                f"   B) 『引き継ぎ準備して』で新セッションへ → 0%から再開（役割・文脈はhandover書で継続）"
            )
            lines.append(
                "   💡 目安: 軽い作業の続き・同じ文脈を保ちたい→A。"
                "大物作業の開始・細部の記憶が重要→B（圧縮は要約のため細部が薄まる）"
            )
            if overall != "CRIT":
                lines.append(
                    f"   （何もしない場合、CRIT({THRESHOLDS['context_pct']['crit']}%)まで"
                    f"あと約{est['remaining_turns_now']}回の入力で到達する見込み）"
                )
    else:
        # legacyフォールバック表示
        lines.append("   ⚠️ usage情報が読めないため旧方式（累計・精度低）で判定:")
        lines.append(f"   📦 累計サイズ: {metrics['size_mb']}MB / 💬 累計入力: {metrics['user_turns']}回")
        if overall in ("WARN", "CRIT"):
            lines.append("   👉 `/compact` で圧縮、または『引き継ぎ準備して』で新セッションへ")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="セッション健康診断（v2: 実コンテキスト方式）")
    parser.add_argument("--quiet", action="store_true",
                        help="OK時は何も出力しない（Stop hook向け）")
    parser.add_argument("--json", action="store_true", help="JSON出力")
    parser.add_argument("--session", type=Path, help="特定セッションを指定")
    parser.add_argument("--window", type=int,
                        help="コンテキスト窓サイズを手動指定（tokens）")
    args = parser.parse_args()

    # 優先順位: ①--session明示指定 ②hookのstdin(transcript_path＝正確)
    #          ③hook起動だが対象未作成＝新セッション→健康扱い(推測しない)
    #          ④stdinなし(手動実行)→mtime推測(最終手段)
    source = "arg"
    if args.session:
        jsonl = args.session
    else:
        jsonl, is_hook = session_from_hook_stdin()
        if jsonl:
            source = "hook"
        elif is_hook:
            # 🔴 引き継ぎ直後など「中身ゼロの新セッション」。
            # 前セッションの巨大jsonlを推測検出してCRIT誤報するのを防ぐため、
            # mtime推測には進まず健康(OK)として静かに抜ける。
            if not args.quiet:
                print("\n✅ セッション健康診断: OK（新セッション開始・容量ゼロ）")
            return 0
        else:
            jsonl = find_current_session()
            source = "guess"
    if not jsonl or not jsonl.exists():
        if not args.quiet:
            print("⚠️  セッションファイルが見つかりません", file=sys.stderr)
        return 0  # quietモードでは終了コード0で抜ける（hookを止めない）

    metrics = analyze_session(jsonl)
    metrics["detect_source"] = source
    window, window_source = resolve_window(metrics, args.window)
    metrics["window_source"] = window_source
    evaluation = evaluate(metrics, window)

    if args.json:
        out = {**metrics, **evaluation}
        if metrics.get("context_tokens"):
            out["compact_estimate"] = estimate_compact_effect(metrics, window)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.quiet and evaluation["overall"] == "OK":
        return 0  # 静かに終了

    report = format_report(metrics, evaluation)
    if source == "guess":
        report += (
            "\n   ⚠️ 注意: 現在セッションを特定できず"
            "『最新更新ファイル』で推測表示しています（hook経由なら正確）。"
        )
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
