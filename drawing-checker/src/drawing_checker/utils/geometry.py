# -*- coding: utf-8 -*-
"""座標系変換・ジオメトリヘルパー"""
from __future__ import annotations

from typing import Optional

from ..model import BBox


def expand_bbox(bbox: BBox, pad: float = 5.0) -> BBox:
    """矩形を外側に pad だけ広げる（注釈用）"""
    return BBox(
        x0=bbox.x0 - pad,
        y0=bbox.y0 - pad,
        x1=bbox.x1 + pad,
        y1=bbox.y1 + pad,
    )


def bbox_overlaps(a: BBox, b: BBox) -> bool:
    """2つの矩形が重なっているか"""
    return not (a.x1 < b.x0 or b.x1 < a.x0 or a.y1 < b.y0 or b.y1 < a.y0)


def bbox_distance(a: BBox, b: BBox) -> float:
    """2つの矩形間の最短距離（重なっていれば0）"""
    if bbox_overlaps(a, b):
        return 0.0
    dx = max(0.0, max(a.x0 - b.x1, b.x0 - a.x1))
    dy = max(0.0, max(a.y0 - b.y1, b.y0 - a.y1))
    return (dx * dx + dy * dy) ** 0.5


def bbox_contains_point(bbox: BBox, x: float, y: float) -> bool:
    return bbox.x0 <= x <= bbox.x1 and bbox.y0 <= y <= bbox.y1


def pt_to_mm(pt: float) -> float:
    """ポイント(pt) → ミリメートル(mm)"""
    return pt * 25.4 / 72.0


def mm_to_pt(mm: float) -> float:
    """ミリメートル(mm) → ポイント(pt)"""
    return mm * 72.0 / 25.4


def unify_bbox(bboxes: list[BBox]) -> Optional[BBox]:
    """複数の矩形を内包する最小の矩形"""
    if not bboxes:
        return None
    x0 = min(b.x0 for b in bboxes)
    y0 = min(b.y0 for b in bboxes)
    x1 = max(b.x1 for b in bboxes)
    y1 = max(b.y1 for b in bboxes)
    return BBox(x0=x0, y0=y0, x1=x1, y1=y1)
