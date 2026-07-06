# -*- coding: utf-8 -*-
"""
検図結果をPDFに直接マーキングする（赤ペン風注釈）

設計方針：
- 人間が一目で「どこに何件」かわかることを最優先
- ポップアップ付箋（📄アイコン）は使わない（PDFビューアで画面を埋める原因）
- 指摘箇所は「枠＋番号バッジ」で示し、詳細はサマリーページに集約
- INFOはPDFには描かずサマリーのみ（読みやすさ最優先）
- 同一箇所の重複指摘は1つにまとめる
- 同じルールの大量検出は20件に制限
"""
from __future__ import annotations

import html as _html
import platform
from collections import defaultdict
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

from ..model import BBox, CheckReport, Drawing, Finding, Severity
from ..utils.geometry import bbox_distance, expand_bbox
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 同じルールの検出数が多すぎるときの上限（スパム抑制）
MAX_PER_RULE = 20
# 近接した指摘を束ねる閾値（pt）
CLUSTER_THRESHOLD_PT = 30.0


# ----------------------------------------------------------------------
# 日本語フォント対応
# ----------------------------------------------------------------------
_JP_FONT_CANDIDATES_WIN = [
    r"C:\Windows\Fonts\meiryo.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc",
    r"C:\Windows\Fonts\YuGothR.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
    r"C:\Windows\Fonts\msmincho.ttc",
]
_JP_FONT_CANDIDATES_MAC = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]
_JP_FONT_CANDIDATES_LINUX = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
]


def _find_jp_font_path() -> Optional[str]:
    """システムにある日本語フォントのパスを返す（無ければNone）"""
    system = platform.system()
    if system == "Windows":
        candidates = _JP_FONT_CANDIDATES_WIN
    elif system == "Darwin":
        candidates = _JP_FONT_CANDIDATES_MAC
    else:
        candidates = _JP_FONT_CANDIDATES_LINUX
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def _insert_jp_text(page, rect, text: str, fontsize: int = 10) -> None:
    """
    日本語対応のテキスト挿入。
    優先度:
      1) insert_htmlbox（新しめPyMuPDFならシステムフォント自動選択）
      2) 日本語フォントファイル＋insert_textbox
      3) Helveticaで英数字だけ表示（日本語は?になる）
    """
    # --- 1) insert_htmlbox（内部でシステムフォント使用）
    try:
        safe = _html.escape(text).replace("\n", "<br/>")
        page.insert_htmlbox(
            rect,
            f'<div style="font-family:sans-serif;font-size:{fontsize}pt;'
            f'white-space:pre-wrap;line-height:1.4">{safe}</div>',
        )
        return
    except Exception:
        pass

    # --- 2) 日本語フォントファイル＋insert_textbox
    font_path = _find_jp_font_path()
    if font_path:
        try:
            page.insert_textbox(
                rect,
                text,
                fontsize=fontsize,
                fontname="jp_font",
                fontfile=font_path,
            )
            return
        except Exception as e:
            logger.warning("日本語フォント読み込み失敗 %s: %s", font_path, e)

    # --- 3) 最後の手段：helv（日本語は?になる）
    page.insert_textbox(rect, text, fontsize=fontsize, fontname="helv")


def annotate(
    drawing: Drawing,
    report: CheckReport,
    output_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """検図結果をマーキングしたPDFを出力して、出力先パスを返す"""
    if fitz is None:
        raise ImportError("PyMuPDFが未インストールです。pip install PyMuPDF")

    src = Path(drawing.source_path)
    if output_path is None:
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / (src.stem + "_checked.pdf")
        else:
            output_path = src.with_name(src.stem + "_checked.pdf")

    if drawing.source_format == "pdf":
        doc = fitz.open(src)
    else:
        doc = _render_non_pdf_to_pdf(drawing)

    try:
        # ★フィルタ＆クラスタリング：描画対象を絞る
        visible = _select_visible_findings(report.findings)

        # ページごとにグルーピング
        by_page: dict[int, list[tuple[int, Finding]]] = defaultdict(list)
        for idx, f in visible:
            by_page[f.page_number].append((idx, f))

        for page_num, items in by_page.items():
            page_index = page_num - 1
            if page_index < 0 or page_index >= doc.page_count:
                continue
            _draw_findings_on_page(doc[page_index], items)

        # サマリーページを先頭に追加（全件）
        _add_summary_page(doc, report)
        doc.save(output_path, deflate=True, garbage=3)
    finally:
        doc.close()

    logger.info("検図PDF出力: %s", output_path)
    return output_path


# ----------------------------------------------------------------------
# 描画対象の選択：見やすくするためのフィルタ
# ----------------------------------------------------------------------
def _select_visible_findings(findings: list[Finding]) -> list[tuple[int, Finding]]:
    """
    PDF上に赤枠で表示する指摘を選ぶ。
    - INFOは表示しない（サマリーページのみ）
    - 同じルールが大量に出ている場合はMAX_PER_RULE件に制限
    - 座標の近い指摘はまとめる
    戻り値：（サマリー上の通し番号, Finding）のリスト
    """
    # 1. INFOを除外
    filtered = [(i + 1, f) for i, f in enumerate(findings)
                if f.severity != Severity.INFO]

    # 2. 同じrule_idの検出を上限まで絞る
    by_rule: dict[str, list[tuple[int, Finding]]] = defaultdict(list)
    for idx, f in filtered:
        by_rule[f.rule_id].append((idx, f))

    limited: list[tuple[int, Finding]] = []
    for rule_id, items in by_rule.items():
        if len(items) > MAX_PER_RULE:
            limited.extend(items[:MAX_PER_RULE])
            logger.info(
                "ルール %s は %d 件検出 → 上位 %d 件のみPDFに表示",
                rule_id, len(items), MAX_PER_RULE,
            )
        else:
            limited.extend(items)

    # 3. bboxが無いものはスキップ（描きようがない）
    limited = [(i, f) for (i, f) in limited if f.bbox is not None]

    # 4. 近接した同種の指摘をクラスタリング
    clustered = _cluster_nearby(limited)
    return clustered


def _cluster_nearby(items: list[tuple[int, Finding]]) -> list[tuple[int, Finding]]:
    """
    座標が近く、かつ同じ severity / rule_id の指摘を統合する。
    同じページ内でのみ統合する。
    """
    # ページ・rule_id・severityでグループ化
    groups: dict[tuple[int, str, str], list[tuple[int, Finding]]] = defaultdict(list)
    for idx, f in items:
        key = (f.page_number, f.rule_id, f.severity.value)
        groups[key].append((idx, f))

    out: list[tuple[int, Finding]] = []
    for _, group in groups.items():
        if len(group) == 1:
            out.extend(group)
            continue
        # 近接でクラスタ化
        used = [False] * len(group)
        for i in range(len(group)):
            if used[i]:
                continue
            bucket = [group[i]]
            used[i] = True
            bi = group[i][1].bbox
            for j in range(i + 1, len(group)):
                if used[j]:
                    continue
                bj = group[j][1].bbox
                if bi and bj and bbox_distance(bi, bj) < CLUSTER_THRESHOLD_PT:
                    bucket.append(group[j])
                    used[j] = True
            # bucket内で最小indexのfindingを代表に（ただしbboxは全体を包む）
            bucket.sort(key=lambda p: p[0])
            rep_idx, rep_finding = bucket[0]
            if len(bucket) > 1:
                # bboxを統合
                xs0 = [b[1].bbox.x0 for b in bucket if b[1].bbox]
                ys0 = [b[1].bbox.y0 for b in bucket if b[1].bbox]
                xs1 = [b[1].bbox.x1 for b in bucket if b[1].bbox]
                ys1 = [b[1].bbox.y1 for b in bucket if b[1].bbox]
                merged_bbox = BBox(min(xs0), min(ys0), max(xs1), max(ys1))
                # 代表のbboxを書き換え
                from dataclasses import replace as _dc_replace
                try:
                    rep_finding = _dc_replace(rep_finding, bbox=merged_bbox)
                except Exception:
                    rep_finding.bbox = merged_bbox  # type: ignore
            out.append((rep_idx, rep_finding))
    # 通し番号順に戻す
    out.sort(key=lambda p: p[0])
    return out


# ----------------------------------------------------------------------
# ページ描画
# ----------------------------------------------------------------------
def _draw_findings_on_page(
    page: "fitz.Page",
    items: list[tuple[int, Finding]],
) -> None:
    # ページが回転している場合、rect と mediabox の向きが異なる
    # 注釈は mediabox 座標系で書く必要があるため高さはmediaboxから取る
    mb = page.mediabox
    page_h = mb.height
    for sequence_num, f in items:
        if f.bbox is None:
            continue
        color = _severity_color(f.severity)

        # PDF座標→fitz座標変換（y反転）
        b = expand_bbox(f.bbox, pad=4.0)
        rect = fitz.Rect(b.x0, page_h - b.y1, b.x1, page_h - b.y0)

        # 枠線（rect annotation）
        annot = page.add_rect_annot(rect)
        annot.set_colors(stroke=color)
        annot.set_border(width=_severity_line_width(f.severity))
        annot.set_opacity(1.0)
        # 注釈の詳細（ビューアで注釈をクリックすると表示される）
        annot.set_info(
            title=f"#{sequence_num}",
            subject=f"[{f.severity.value.upper()}] {f.rule_id}",
            content=_compose_note(f),
        )
        annot.update()

        # 左上に番号バッジ（円＋数字）を描く
        _draw_number_badge(page, rect, sequence_num, color)


def _draw_number_badge(
    page: "fitz.Page",
    rect: "fitz.Rect",
    num: int,
    color: tuple[float, float, float],
) -> None:
    """矩形の左上に番号バッジを描く"""
    radius = 7.0
    cx = rect.x0
    cy = rect.y0  # fitz座標の左上
    badge_rect = fitz.Rect(cx - radius, cy - radius, cx + radius, cy + radius)

    # 背景の塗りつぶし円（白に近い淡色で可読性UP）
    page.draw_circle(
        center=(cx, cy),
        radius=radius,
        color=color,
        fill=color,
        width=0.5,
    )
    # 番号テキスト（数字のみなのでhelvでOK）
    label = str(num)
    fontsize = 8 if num < 10 else (7 if num < 100 else 6)
    # 中央配置のため少し調整
    text_x = cx - (fontsize * 0.28 * len(label))
    text_y = cy + (fontsize * 0.35)
    try:
        page.insert_text(
            (text_x, text_y),
            label,
            fontsize=fontsize,
            color=(1, 1, 1),  # 白文字
            fontname="helv",
        )
    except Exception:
        pass


def _severity_color(severity: Severity) -> tuple[float, float, float]:
    if severity == Severity.ERROR:
        return (0.90, 0.15, 0.15)  # 赤
    if severity == Severity.WARNING:
        return (0.95, 0.55, 0.05)  # オレンジ
    return (0.15, 0.50, 0.95)       # 青（通常は描かないが保険）


def _severity_line_width(severity: Severity) -> float:
    if severity == Severity.ERROR:
        return 2.2
    if severity == Severity.WARNING:
        return 1.4
    return 1.0


def _compose_note(f: Finding) -> str:
    parts = [f.message]
    if f.jis_reference:
        parts.append(f"根拠: {f.jis_reference}")
    if f.suggestion:
        parts.append(f"修正案: {f.suggestion}")
    return "\n".join(parts)


# ----------------------------------------------------------------------
# 非PDF → PDFレンダリング（簡易）
# ----------------------------------------------------------------------
def _render_non_pdf_to_pdf(drawing: Drawing) -> "fitz.Document":
    """DXF/DWG/画像/SLDDRWの場合、簡易的に空のPDFを作成し、各ページに情報を書く"""
    doc = fitz.open()
    src = Path(drawing.source_path)
    for page in drawing.pages:
        w = max(page.width, 595)
        h = max(page.height, 842)
        pdf_page = doc.new_page(width=w, height=h)
        info = (
            f"drawing-checker 検図対象\n"
            f"ファイル: {src.name}\n"
            f"形式: {drawing.source_format}\n"
            f"ページ: {page.page_number}\n"
            f"エンティティ数: {len(page.entities)}\n"
            f"寸法数: {len(page.dimensions)}"
        )
        _insert_jp_text(
            pdf_page,
            fitz.Rect(30, 30, w - 30, 200),
            info,
            fontsize=11,
        )
    return doc


# ----------------------------------------------------------------------
# サマリーページ
# ----------------------------------------------------------------------
def _add_summary_page(doc: "fitz.Document", report: CheckReport) -> None:
    if doc.page_count == 0:
        return
    first = doc[0]
    # 回転を考慮しない固定A4縦サイズでサマリーを作る
    # （元PDFが90度回転等でもサマリーは普通に読めるように）
    width = 595
    height = 842
    page = doc.new_page(pno=0, width=width, height=height)
    # 新規ページなので回転なし

    status = "合格" if report.is_pass else "不合格（要修正）"

    header_lines = [
        "検図サマリー",
        "",
        f"対象: {Path(report.drawing_path).name}",
        f"判定: {status}",
        f"エラー(ERROR):   {report.errors_count} 件",
        f"警告(WARNING):   {report.warnings_count} 件",
        f"情報(INFO):      {report.info_count} 件",
        f"処理時間:        {report.processing_time_sec:.2f} 秒",
        "",
        "※ 図面上の赤丸(ERROR)・橙丸(WARNING)の番号は下記一覧の番号と対応します",
        "※ INFOは図面には表示されません（下の一覧でのみ確認）",
        "",
        "--- 指摘一覧 ---",
    ]

    detail_lines: list[str] = []
    for i, f in enumerate(report.findings, 1):
        mark = {"error": "[!!]", "warning": "[! ]", "info": "[i ]"}.get(f.severity.value, "")
        detail_lines.append(
            f"{i:>3}. {mark} {f.rule_id}  p.{f.page_number}  {f.message}"
        )
        if f.jis_reference:
            detail_lines.append(f"       根拠: {f.jis_reference}")
        if f.suggestion:
            detail_lines.append(f"       修正案: {f.suggestion}")

    text = "\n".join(header_lines + detail_lines)
    _insert_jp_text(
        page,
        fitz.Rect(30, 30, width - 30, height - 30),
        text,
        fontsize=9,
    )
