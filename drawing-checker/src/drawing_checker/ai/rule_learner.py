# -*- coding: utf-8 -*-
"""
サンプル図面からルールを自動生成する。

入力：キレイな図面（社内標準準拠）のPDF/DXFを5〜10枚
出力：config/learned_rules.json

処理：
1. 各図面をパース → 統計的に共通パターンを抽出
   - 使われているタイトルブロックフィールドとキーワード
   - 使われている公差等級の傾向
   - 使われている表面粗さ表記の傾向
   - 使われているレイヤー/線種の傾向
2. Geminiに「この図面群から読み取れる社内固有ルール」を問い合わせて統合
3. JIS規格との差分を検出 → サンプル側の表記を「会社ルール」として登録
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ..model import Drawing
from ..parsers import dispatch
from ..utils.logger import get_logger
from .gemini_client import GeminiClient

logger = get_logger(__name__)


def learn(
    sample_files: list[Path],
    output_path: Path,
    use_ai: bool = True,
) -> dict[str, Any]:
    """サンプル図面からルールを生成し、JSONファイルに保存"""
    drawings: list[Drawing] = []
    for f in sample_files:
        try:
            drawings.append(dispatch.parse(f))
        except Exception as e:
            logger.warning("サンプル解析失敗 %s: %s", f, e)

    if not drawings:
        logger.error("有効なサンプルが1つもありません")
        return {}

    # 統計的特徴の抽出
    stats = _extract_statistics(drawings)

    # ルールJSONを構築
    rules = _build_rules_from_stats(stats)

    # AI補完（任意）
    if use_ai:
        ai_rules = _ai_generate_rules(drawings, stats)
        if ai_rules:
            # AIが提案するルールは override_by_sample=True で追加
            existing_ids = {r["id"] for r in rules}
            for r in ai_rules:
                if r.get("id") not in existing_ids:
                    rules.append(r)

    result = {
        "version": "1.0",
        "learned_from_samples": [str(p) for p in sample_files],
        "sample_count": len(drawings),
        "rules": rules,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("ルール学習完了: %s（%d件のルール）", output_path, len(rules))
    return result


# ----------------------------------------------------------------------
# 統計抽出
# ----------------------------------------------------------------------
def _extract_statistics(drawings: list[Drawing]) -> dict[str, Any]:
    tolerance_counter: Counter[str] = Counter()
    surface_counter: Counter[str] = Counter()
    layer_counter: Counter[str] = Counter()
    title_block_keywords: Counter[str] = Counter()
    sheet_size_counter: Counter[str] = Counter()

    for d in drawings:
        for p in d.pages:
            text = p.raw_text
            # 公差クラス
            for m in re.finditer(r"\b([Hh]\d+|[Jj][Ss]\d+|[Pp]\d+|[Gg]\d+|[Ff]\d+|[Ee]\d+)\b", text):
                tolerance_counter[m.group(1)] += 1
            # 表面粗さ
            for m in re.finditer(r"Ra\s*[\d.]+", text, re.IGNORECASE):
                surface_counter[m.group(0)] += 1
            # レイヤー
            for e in p.entities:
                if e.layer:
                    layer_counter[e.layer] += 1
            # タイトルブロックによくある単語
            for kw in ["図番", "品名", "材質", "尺度", "設計", "承認", "検図", "日付",
                       "第三角法", "普通公差"]:
                if kw in text:
                    title_block_keywords[kw] += 1
            # 用紙サイズ
            if p.sheet_size:
                sheet_size_counter[p.sheet_size] += 1

    return {
        "tolerance_classes": tolerance_counter.most_common(10),
        "surface_roughness": surface_counter.most_common(5),
        "layers": layer_counter.most_common(20),
        "title_block_keywords": title_block_keywords.most_common(),
        "sheet_sizes": sheet_size_counter.most_common(),
    }


# ----------------------------------------------------------------------
# 統計→ルール
# ----------------------------------------------------------------------
def _build_rules_from_stats(stats: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []

    # タイトルブロックキーワード：よく登場するものを「必須」として登録
    common_keywords = [kw for kw, cnt in stats["title_block_keywords"] if cnt >= 2]
    if common_keywords:
        rules.append({
            "id": "LEARNED-TITLE-001",
            "name": "社内標準タイトルブロックキーワード",
            "category": "title_block",
            "checker": "title_block_checker",
            "severity": "warning",
            "override_by_sample": True,
            "description": "サンプル図面で共通して登場するタイトルブロック項目",
            "keywords": common_keywords,
        })

    # 使われている公差クラスをホワイトリスト化
    if stats["tolerance_classes"]:
        preferred = [tc for tc, _cnt in stats["tolerance_classes"]]
        rules.append({
            "id": "LEARNED-TOL-001",
            "name": "社内採用公差クラス",
            "category": "tolerance",
            "checker": "dimension_checker",
            "severity": "info",
            "override_by_sample": True,
            "description": "サンプル図面で使用されている公差クラスの傾向",
            "preferred_classes": preferred,
        })

    # 使われているレイヤー命名規約
    if stats["layers"]:
        rules.append({
            "id": "LEARNED-LAYER-001",
            "name": "社内採用レイヤー構成",
            "category": "line_style",
            "checker": "line_style_checker",
            "severity": "info",
            "override_by_sample": True,
            "description": "サンプル図面のレイヤー構成（頻出順）",
            "layers": [lyr for lyr, _cnt in stats["layers"]],
        })

    return rules


# ----------------------------------------------------------------------
# AI補完
# ----------------------------------------------------------------------
def _ai_generate_rules(drawings: list[Drawing], stats: dict[str, Any]) -> list[dict[str, Any]]:
    """Geminiにサンプル図面の特徴から社内ルール候補を生成させる"""
    client = GeminiClient()
    if not client.available:
        return []

    # プロンプト用に軽量化した要約を渡す（画像は現状渡さない＝テキストのみ）
    summary = {
        "sample_count": len(drawings),
        "tolerance_classes": stats["tolerance_classes"],
        "surface_roughness": stats["surface_roughness"],
        "layers": stats["layers"],
        "title_block_keywords": stats["title_block_keywords"],
        "sheet_sizes": stats["sheet_sizes"],
        "sample_texts_preview": [
            (d.pages[0].raw_text[:500] if d.pages else "") for d in drawings[:3]
        ],
    }

    prompt = f"""あなたは機械設計図面（JIS準拠）の検図の専門家です。
以下は、ある企業の「合格図面」サンプル群から抽出した統計情報です。

```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

この情報から読み取れる、JIS標準には明示されていない
「この会社特有の検図ルール候補」を3〜5個提案してください。
フォーマットは以下のJSON配列としてください。

```json
[
  {{
    "id": "LEARNED-AI-001",
    "name": "ルール名",
    "category": "title_block|tolerance|line_style|surface|dimension|geometric_tolerance|welding|general",
    "checker": "title_block_checker|dimension_checker|line_style_checker|symbol_checker",
    "severity": "error|warning|info",
    "override_by_sample": true,
    "description": "ルールの説明",
    "rationale": "サンプルからそう推測した理由"
  }}
]
```
"""
    result = client.generate_json(prompt, temperature=0.3)
    if not isinstance(result, list):
        return []

    # バリデーション（必要最低限のキーが揃っているか）
    required = {"id", "name", "checker", "severity"}
    cleaned: list[dict[str, Any]] = []
    for i, r in enumerate(result):
        if not isinstance(r, dict):
            continue
        if not required.issubset(r.keys()):
            continue
        r.setdefault("override_by_sample", True)
        cleaned.append(r)
    return cleaned
