# -*- coding: utf-8 -*-
"""
画像パーサー（PNG/JPG）

- OpenCVで画像読み込み＋線検出（Houghlines）
- pytesseract で日本語OCR（jpn+eng）
- 精度は低いので最終手段扱い
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    import cv2  # OpenCV
    import numpy as np
    import pytesseract
    from PIL import Image
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore
    np = None   # type: ignore
    pytesseract = None  # type: ignore
    Image = None  # type: ignore

from ..model import (
    BBox,
    Drawing,
    Entity,
    EntityType,
    LineStyle,
    Page,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


def parse(path: str | Path) -> Drawing:
    if cv2 is None or pytesseract is None:
        raise ImportError(
            "opencv-python / pytesseract / pillow が未インストールです。"
            "pip install opencv-python pytesseract pillow を実行してください。"
        )

    path = Path(path)
    # Tesseractパス設定
    tess_path = os.environ.get("TESSERACT_PATH")
    if tess_path and Path(tess_path).exists():
        pytesseract.pytesseract.tesseract_cmd = tess_path

    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"画像読み込みに失敗しました: {path}")
    h, w = img.shape[:2]

    entities: list[Entity] = []
    raw_text = ""

    # ------------------------------------------------------------------
    # OCR（日本語+英語）
    # ------------------------------------------------------------------
    try:
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        data = pytesseract.image_to_data(
            pil_img,
            lang="jpn+eng",
            output_type=pytesseract.Output.DICT,
        )
        lines: list[str] = []
        for i, text in enumerate(data["text"]):
            text = (text or "").strip()
            if not text:
                continue
            x = float(data["left"][i])
            y = float(data["top"][i])
            ww = float(data["width"][i])
            hh = float(data["height"][i])
            # 画像座標（左上原点）→ PDF風座標（左下原点）に合わせる
            bbox = BBox(x0=x, y0=h - (y + hh), x1=x + ww, y1=h - y)
            entities.append(
                Entity(
                    type=EntityType.TEXT,
                    bbox=bbox,
                    text=text,
                    raw={"source": "ocr"},
                )
            )
            lines.append(text)
        raw_text = "\n".join(lines)
    except Exception as e:
        logger.warning("OCR失敗: %s", e)

    # ------------------------------------------------------------------
    # 線検出（Hough変換）
    # ------------------------------------------------------------------
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(
            edges, rho=1, theta=np.pi / 180,
            threshold=100, minLineLength=30, maxLineGap=10,
        )
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                bbox = BBox(
                    x0=float(min(x1, x2)),
                    y0=float(h - max(y1, y2)),
                    x1=float(max(x1, x2)),
                    y1=float(h - min(y1, y2)),
                )
                entities.append(
                    Entity(
                        type=EntityType.LINE,
                        bbox=bbox,
                        line_style=LineStyle.UNKNOWN,
                        raw={"source": "hough"},
                    )
                )
    except Exception as e:
        logger.warning("線検出失敗: %s", e)

    page = Page(
        page_number=1,
        width=float(w),
        height=float(h),
        entities=entities,
        raw_text=raw_text,
    )
    return Drawing(
        source_path=str(path),
        source_format="image",
        pages=[page],
        meta={"width": w, "height": h},
    )
