# -*- coding: utf-8 -*-
"""
製作可能性チェッカー（AI駆動）

機械設計図面に対して、以下2つの観点から検図する：

  1. 加工に必須な寸法が抜けていないか
     - 穴の位置（座標）・直径・深さ
     - ねじ仕様（呼び径×ピッチ、下穴、深さ）
     - ザグリ・皿モミの寸法
     - 外形寸法・板厚
     - はめあい公差が必要な箇所
     - キー溝・段付き部の寸法

  2. 加工自体が困難/不可能な図面になっていないか
     - 工具が届かない形状
     - 刃物の半径より小さい内部角
     - 極端に深い細穴（L/D比過大）
     - 材質に対して不適切な公差
     - 相互に矛盾する寸法
     - 現実的でない表面粗さ指定

PDFページを画像化してGemini 2.5 Flashに渡し、文字だけでは分からない
視覚的な不備も検出できるようにする。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

from ..model import BBox, CheckReport, Drawing, Finding, Severity
from ..utils.logger import get_logger
from .gemini_client import GeminiClient

logger = get_logger(__name__)


# 画像化の解像度（検図に十分な精度、かつAPIトークン消費を抑えるバランス）
RENDER_DPI = 150


def run(drawing: Drawing, report: CheckReport) -> None:
    """Drawingを製作可能性の観点で分析し、指摘をreportに追加"""
    client = GeminiClient()
    if not client.available:
        logger.info("Gemini未使用のため製作可能性チェックをスキップ")
        return

    # ページごとに画像化して分析
    for page in drawing.pages:
        image_bytes = _render_page_to_png(drawing, page.page_number)
        if image_bytes is None:
            continue
        findings = _analyze_page(client, page, image_bytes)
        for f in findings:
            report.add(f)


# ----------------------------------------------------------------------
# ページ画像化
# ----------------------------------------------------------------------
def _render_page_to_png(drawing: Drawing, page_number: int) -> Optional[bytes]:
    """指定ページをPNG画像にレンダリング"""
    if fitz is None:
        return None
    try:
        src = Path(drawing.source_path)
        if drawing.source_format != "pdf":
            return None  # PDF以外は一旦スキップ（画像パーサーで取得したものを渡せば拡張可能）

        doc = fitz.open(src)
        try:
            if page_number < 1 or page_number > doc.page_count:
                return None
            page = doc[page_number - 1]
            mat = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")
        finally:
            doc.close()
    except Exception as e:
        logger.warning("ページ画像化失敗 (p.%d): %s", page_number, e)
        return None


# ----------------------------------------------------------------------
# 分析
# ----------------------------------------------------------------------
PROMPT_TEMPLATE = """あなたは機械加工の現場を熟知したベテラン検図者です。
添付の図面を見て、**加工現場の視点**で以下の2点を厳密にチェックしてください。

## 視点1：加工に必須な寸法の欠落
加工者がこの図面だけを見て部品を作るとき、**必ず必要なのに書かれていない寸法**を列挙。
例：
- 穴があるが、穴の位置寸法（基準からの距離）が書かれていない
- 穴の直径はあるが、深さが書かれていない（貫通か止まりか不明）
- ねじ記号（M4, M6等）があるがピッチ/深さ/下穴が不明
- 段付き形状があるのに段差の寸法がない
- キー溝があるのに幅・深さ・位置が不明
- はめあい穴なのに公差指示が無い
- 板厚・奥行きなど立体として必須な寸法が無い
- ザグリ/皿モミがあるのに寸法が無い
- 面取り/R指示があるが数値が無い

## 視点2：加工が困難・不可能な箇所
加工者の視点で「これ、どうやって作るの？」という箇所を列挙。
例：
- 工具（エンドミル等）が入らない形状（内部の鋭角コーナー、深すぎる狭いポケット）
- 公差が材料・工程に対して厳しすぎる（例：溶接後のプレス部に±0.01）
- 表面粗さ指定が現実的でない（Ra0.05を通常ミーリングで、など）
- 寸法が相互に矛盾（合計値が合わない、同じ箇所を異なる基準で過剰定義）
- 基準が不明確で加工治具が組めない
- 極端に薄い壁（工具径より薄い）・深い細穴（L/D > 10）
- 材質に対して無理な形状

## 出力形式
JSON配列で、1件ずつ具体的に。根拠のない憶測は避け、**図面から読み取れる客観的事実**のみ指摘。
完璧な図面なら空配列 [] を返す。

[
  {
    "severity": "error" | "warning" | "info",
    "category": "missing_dim" | "manufacturability",
    "message": "80文字以内の具体的な指摘（どの箇所の、何が、なぜ問題か）",
    "suggestion": "修正提案（50文字以内）",
    "location_hint": "図面上の位置のヒント（例：左上の穴、タイトルブロック横の段付き部）"
  }
]

## 補足情報
- 形式: {source_format}
- 抽出済み寸法数: {dim_count}件
- 抽出済み寸法例: {dim_samples}
- タイトルブロック: {title_block}
"""


def _analyze_page(client: GeminiClient, page, image_bytes: bytes) -> list[Finding]:
    """1ページを分析してFindingsを返す"""
    dim_samples = [
        f"{d.value}"
        for d in page.dimensions[:25]
        if d.value
    ]
    title_block_str = "なし"
    if page.title_block and page.title_block.fields:
        title_block_str = ", ".join(
            f"{k}={v}" for k, v in list(page.title_block.fields.items())[:8]
        )

    prompt = PROMPT_TEMPLATE.format(
        source_format="PDF",
        dim_count=len(page.dimensions),
        dim_samples=", ".join(dim_samples) or "(抽出できず)",
        title_block=title_block_str,
    )

    result = client.generate_json_with_image(
        prompt, image_bytes, mime_type="image/png", temperature=0.15,
    )

    if not isinstance(result, list):
        return []

    findings: list[Finding] = []
    for item in result:
        if not isinstance(item, dict):
            continue

        sev_str = (item.get("severity") or "warning").lower()
        try:
            sev = Severity(sev_str)
        except ValueError:
            sev = Severity.WARNING

        category = (item.get("category") or "").lower()
        if category == "missing_dim":
            rule_id = "MFG-MISSING-DIM"
            tag = "寸法欠落"
        elif category == "manufacturability":
            rule_id = "MFG-INFEASIBLE"
            tag = "加工困難"
        else:
            rule_id = "MFG-AI"
            tag = "製作性"

        message = str(item.get("message") or "").strip()[:200]
        suggestion = str(item.get("suggestion") or "").strip()[:120]
        location = str(item.get("location_hint") or "").strip()[:80]

        # ロケーションヒントをメッセージに織り込む
        full_message = f"【{tag}】{message}"
        if location:
            full_message += f"（位置: {location}）"

        findings.append(
            Finding(
                checker="manufacturability_checker",
                rule_id=rule_id,
                severity=sev,
                message=full_message,
                page_number=page.page_number,
                bbox=None,
                suggestion=suggestion,
                jis_reference="",
            )
        )
    return findings
