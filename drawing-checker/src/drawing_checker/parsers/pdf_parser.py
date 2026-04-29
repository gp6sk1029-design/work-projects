# -*- coding: utf-8 -*-
"""
PDFパーサー（PyMuPDF使用）

- テキストとその座標を抽出
- ベクター情報から線種・太さを推定
- 寸法記号（φ、R、×、°）を正規表現で検出
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

from ..model import (
    BBox,
    Dimension,
    Drawing,
    Entity,
    EntityType,
    LineStyle,
    Page,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


# 寸法値を含むテキストの検出パターン
DIMENSION_PATTERN = re.compile(
    r"(?P<prefix>[φØR])?\s*"              # φ/Ø/R プレフィックス
    r"(?P<value>\d+(?:\.\d+)?)"            # 数値
    r"(?P<tolerance>[Hh]\d+|[Jj][Ss]\d+|"  # 公差（H7, JS6等）
    r"[±\+\-]\d+(?:\.\d+)?|[PpGgFf]\d+)?"
)

ANGLE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*°")


def parse(path: str | Path) -> Drawing:
    """PDFを解析して Drawing モデルを返す"""
    if fitz is None:
        raise ImportError(
            "PyMuPDF (fitz) が未インストールです。pip install PyMuPDF を実行してください。"
        )

    path = Path(path)
    doc = fitz.open(path)
    pages: list[Page] = []

    try:
        for page_index in range(doc.page_count):
            pages.append(_parse_page(doc[page_index], page_index))
    finally:
        doc.close()

    return Drawing(
        source_path=str(path),
        source_format="pdf",
        pages=pages,
        meta={"page_count": len(pages)},
    )


def _parse_page(page: "fitz.Page", index: int) -> Page:
    rect = page.rect
    width_pt = float(rect.width)
    height_pt = float(rect.height)

    entities: list[Entity] = []
    dimensions: list[Dimension] = []

    raw_text_parts: list[str] = []

    # ------------------------------------------------------------------
    # テキストブロック抽出
    # ------------------------------------------------------------------
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:  # 画像ブロックはスキップ
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                x0, y0, x1, y1 = span["bbox"]
                # PyMuPDF: 原点左上・y下向き → PDF標準: 原点左下・y上向き に変換
                pdf_y0 = height_pt - y1
                pdf_y1 = height_pt - y0
                bbox = BBox(x0=x0, y0=pdf_y0, x1=x1, y1=pdf_y1)
                raw_text_parts.append(text)

                entities.append(
                    Entity(
                        type=EntityType.TEXT,
                        bbox=bbox,
                        text=text,
                        color=_argb_to_hex(span.get("color", 0)),
                        raw={"font": span.get("font"), "size": span.get("size")},
                    )
                )

                # 寸法らしき文字列を抽出
                dim = _try_parse_dimension(text, bbox)
                if dim:
                    dimensions.append(dim)

    # ------------------------------------------------------------------
    # 図形（ベクター）抽出
    # ------------------------------------------------------------------
    try:
        drawings = page.get_drawings()
    except Exception as e:
        logger.debug("get_drawings failed: %s", e)
        drawings = []

    for d in drawings:
        rect_b = d.get("rect")
        if rect_b is None:
            continue
        x0, y0, x1, y1 = rect_b
        pdf_y0 = height_pt - y1
        pdf_y1 = height_pt - y0
        bbox = BBox(x0=x0, y0=pdf_y0, x1=x1, y1=pdf_y1)

        line_width = float(d.get("width") or 0.0)
        dashes = d.get("dashes") or ""
        line_style = _classify_line_style(dashes, line_width)

        items = d.get("items") or []
        etype = _classify_entity(items)

        entities.append(
            Entity(
                type=etype,
                bbox=bbox,
                line_style=line_style,
                line_width=line_width,
                color=_normalize_color(d.get("color")),
                raw={"items_count": len(items), "dashes": dashes},
            )
        )

    raw_text = "\n".join(raw_text_parts)

    return Page(
        page_number=index + 1,
        width=width_pt,
        height=height_pt,
        entities=entities,
        dimensions=dimensions,
        raw_text=raw_text,
    )


# ----------------------------------------------------------------------
# 補助関数
# ----------------------------------------------------------------------
def _try_parse_dimension(text: str, bbox: BBox) -> Dimension | None:
    """テキストから寸法値を抽出してDimensionを作る"""
    m = DIMENSION_PATTERN.search(text)
    if not m:
        am = ANGLE_PATTERN.search(text)
        if am:
            try:
                return Dimension(
                    bbox=bbox,
                    value=text,
                    numeric_value=float(am.group(1)),
                    raw={"kind": "angle"},
                )
            except ValueError:
                return None
        return None

    prefix = m.group("prefix") or ""
    value_str = m.group("value")
    tol = m.group("tolerance")
    try:
        numeric = float(value_str)
    except ValueError:
        return None

    return Dimension(
        bbox=bbox,
        value=text,
        numeric_value=numeric,
        tolerance=tol,
        is_diameter=prefix in ("φ", "Ø"),
        is_radius=prefix == "R",
        raw={"matched": m.group(0)},
    )


def _classify_line_style(dashes: Any, width: float) -> LineStyle:
    """破線情報と太さからJIS線種を推定"""
    dashes_str = str(dashes or "").strip()
    if not dashes_str or dashes_str == "[] 0":
        return LineStyle.CONTINUOUS
    # 1個の値 → 単純破線 → 隠れ線
    # 2個の値で長さ比が大きい → 一点鎖線の可能性
    # ざっくり分類（DXFでは精密に判定、PDFではヒューリスティック）
    nums = re.findall(r"[\d.]+", dashes_str)
    if len(nums) >= 4:
        return LineStyle.CENTER
    if len(nums) >= 2:
        return LineStyle.HIDDEN
    return LineStyle.CONTINUOUS


def _classify_entity(items: list[Any]) -> EntityType:
    """drawing itemsからエンティティ種別を判定"""
    if not items:
        return EntityType.UNKNOWN
    kinds = {item[0] for item in items if item}
    if "c" in kinds:  # curve
        return EntityType.ARC
    if "re" in kinds:  # rectangle
        return EntityType.POLYLINE
    if "l" in kinds:
        if len(items) > 2:
            return EntityType.POLYLINE
        return EntityType.LINE
    return EntityType.UNKNOWN


def _argb_to_hex(color: int) -> str:
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"


def _normalize_color(color: Any) -> str:
    """PyMuPDFの色（RGB float tuple or None）を#RRGGBBに変換"""
    if not color:
        return "#000000"
    try:
        r, g, b = color[:3]
        return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"
    except Exception:
        return "#000000"
