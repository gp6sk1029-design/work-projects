# -*- coding: utf-8 -*-
"""
DXFパーサー（ezdxf使用）

エンティティ・寸法・レイヤー情報を構造化データで取得できるので、
PDFより高精度な検図が可能。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import ezdxf
    from ezdxf.document import Drawing as DxfDoc
except ImportError:  # pragma: no cover
    ezdxf = None  # type: ignore
    DxfDoc = None  # type: ignore

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


# レイヤー名からJIS線種を推定するためのキーワード
LAYER_HINTS = {
    LineStyle.CONTINUOUS: ["outline", "外形", "外形線", "contour", "visible"],
    LineStyle.HIDDEN:     ["hidden", "隠れ", "隠れ線", "dashed"],
    LineStyle.CENTER:     ["center", "中心", "中心線"],
    LineStyle.PHANTOM:    ["phantom", "想像"],
    LineStyle.DIMENSION:  ["dim", "dimension", "寸法"],
}

# DXFの線種名（LTYPE）からJIS線種を推定
LINETYPE_HINTS = {
    LineStyle.HIDDEN:  ["DASHED", "HIDDEN", "DASH"],
    LineStyle.CENTER:  ["CENTER", "CHAIN"],
    LineStyle.PHANTOM: ["PHANTOM"],
}


def parse(path: str | Path) -> Drawing:
    if ezdxf is None:
        raise ImportError(
            "ezdxf が未インストールです。pip install ezdxf を実行してください。"
        )

    path = Path(path)
    try:
        doc = ezdxf.readfile(str(path))
    except Exception as e:
        logger.warning("DXF読み込み失敗、recoverでリトライ: %s", e)
        from ezdxf import recover
        doc, _ = recover.readfile(str(path))

    page = _parse_modelspace(doc)
    return Drawing(
        source_path=str(path),
        source_format="dxf",
        pages=[page],
        meta={
            "dxf_version": doc.dxfversion,
            "layers": [l.dxf.name for l in doc.layers],
        },
    )


def _parse_modelspace(doc: "DxfDoc") -> Page:
    msp = doc.modelspace()

    # レイヤー名→LineStyleのマッピング
    layer_style_map: dict[str, LineStyle] = {}
    for layer in doc.layers:
        layer_style_map[layer.dxf.name] = _classify_layer(layer.dxf.name)

    entities: list[Entity] = []
    dimensions: list[Dimension] = []
    raw_texts: list[str] = []

    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    for ent in msp:
        dxftype = ent.dxftype()
        layer_name = getattr(ent.dxf, "layer", "")

        try:
            bbox = _entity_bbox(ent)
        except Exception:
            continue
        if bbox is None:
            continue

        # 全体バウンディング更新
        min_x = min(min_x, bbox.x0)
        min_y = min(min_y, bbox.y0)
        max_x = max(max_x, bbox.x1)
        max_y = max(max_y, bbox.y1)

        line_style = layer_style_map.get(layer_name, LineStyle.UNKNOWN)
        if line_style == LineStyle.UNKNOWN:
            # LTYPE から推定
            ltype = getattr(ent.dxf, "linetype", "BYLAYER")
            line_style = _classify_linetype(ltype)

        if dxftype == "DIMENSION":
            dim = _extract_dimension(ent, bbox)
            if dim:
                dimensions.append(dim)
                entities.append(
                    Entity(
                        type=EntityType.DIMENSION,
                        bbox=bbox,
                        layer=layer_name,
                        line_style=LineStyle.DIMENSION,
                        text=dim.value,
                        raw={"dxftype": dxftype},
                    )
                )
            continue

        if dxftype in ("TEXT", "MTEXT"):
            try:
                text = ent.plain_text() if dxftype == "MTEXT" else ent.dxf.text
            except Exception:
                text = ""
            raw_texts.append(text)
            entities.append(
                Entity(
                    type=EntityType.TEXT,
                    bbox=bbox,
                    layer=layer_name,
                    line_style=line_style,
                    text=text,
                    raw={"dxftype": dxftype},
                )
            )
            continue

        etype = _dxftype_to_entitytype(dxftype)
        entities.append(
            Entity(
                type=etype,
                bbox=bbox,
                layer=layer_name,
                line_style=line_style,
                raw={"dxftype": dxftype},
            )
        )

    # ページサイズはモデル空間の範囲から推定
    if min_x == float("inf"):
        width = height = 1000.0
    else:
        width = max_x - min_x
        height = max_y - min_y

    raw_text = "\n".join(raw_texts)
    return Page(
        page_number=1,
        width=width,
        height=height,
        entities=entities,
        dimensions=dimensions,
        raw_text=raw_text,
    )


# ----------------------------------------------------------------------
# 補助関数
# ----------------------------------------------------------------------
def _classify_layer(layer_name: str) -> LineStyle:
    name_lower = layer_name.lower()
    for style, keywords in LAYER_HINTS.items():
        if any(kw.lower() in name_lower for kw in keywords):
            return style
    return LineStyle.UNKNOWN


def _classify_linetype(ltype: str) -> LineStyle:
    ltype_upper = (ltype or "").upper()
    if ltype_upper in ("CONTINUOUS", "BYLAYER", "BYBLOCK", ""):
        return LineStyle.CONTINUOUS
    for style, keywords in LINETYPE_HINTS.items():
        if any(kw in ltype_upper for kw in keywords):
            return style
    return LineStyle.UNKNOWN


def _dxftype_to_entitytype(dxftype: str) -> EntityType:
    mapping = {
        "LINE": EntityType.LINE,
        "LWPOLYLINE": EntityType.POLYLINE,
        "POLYLINE": EntityType.POLYLINE,
        "CIRCLE": EntityType.CIRCLE,
        "ARC": EntityType.ARC,
        "ELLIPSE": EntityType.ELLIPSE,
        "TEXT": EntityType.TEXT,
        "MTEXT": EntityType.TEXT,
        "DIMENSION": EntityType.DIMENSION,
        "LEADER": EntityType.LEADER,
        "HATCH": EntityType.HATCH,
        "INSERT": EntityType.BLOCK,
    }
    return mapping.get(dxftype, EntityType.UNKNOWN)


def _entity_bbox(ent: Any) -> BBox | None:
    """エンティティのバウンディングボックスを取得"""
    try:
        from ezdxf import bbox as _bbox_mod
        bb = _bbox_mod.extents([ent])
        if not bb.has_data:
            return None
        return BBox(
            x0=float(bb.extmin.x),
            y0=float(bb.extmin.y),
            x1=float(bb.extmax.x),
            y1=float(bb.extmax.y),
        )
    except Exception:
        return None


def _extract_dimension(ent: Any, bbox: BBox) -> Dimension | None:
    """DIMENSIONエンティティから数値・公差を抽出"""
    try:
        text = ent.dxf.text if hasattr(ent.dxf, "text") else ""
    except Exception:
        text = ""

    # 測定値（actual measurement）もあれば取る
    try:
        actual = ent.get_measurement() if hasattr(ent, "get_measurement") else None
    except Exception:
        actual = None

    value_text = text if text and text != "<>" else (str(actual) if actual is not None else "")

    # 公差・直径/半径を判定
    is_diameter = "φ" in value_text or "Ø" in value_text or "%%c" in value_text.lower()
    is_radius = value_text.upper().startswith("R")

    numeric_value: float | None = None
    if actual is not None:
        try:
            numeric_value = float(actual)
        except (TypeError, ValueError):
            numeric_value = None

    return Dimension(
        bbox=bbox,
        value=value_text,
        numeric_value=numeric_value,
        is_diameter=is_diameter,
        is_radius=is_radius,
        layer=getattr(ent.dxf, "layer", ""),
        raw={"dxftype": ent.dxftype()},
    )
