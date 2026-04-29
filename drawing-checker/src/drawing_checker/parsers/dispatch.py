# -*- coding: utf-8 -*-
"""
拡張子から適切なパーサーを選んで Drawing を返す。

対応拡張子：
  .pdf                 → pdf_parser
  .dxf                 → dxf_parser
  .dwg                 → dwg_converter → dxf_parser
  .slddrw              → swx_parser
  .png / .jpg / .jpeg  → image_parser
"""
from __future__ import annotations

from pathlib import Path

from ..model import Drawing
from ..utils.logger import get_logger

logger = get_logger(__name__)


def parse(path: str | Path) -> Drawing:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {path}")

    ext = path.suffix.lower()
    if ext == ".pdf":
        from . import pdf_parser
        return pdf_parser.parse(path)
    if ext == ".dxf":
        from . import dxf_parser
        return dxf_parser.parse(path)
    if ext == ".dwg":
        from . import dwg_converter, dxf_parser
        dxf_path = dwg_converter.convert_to_dxf(path)
        return dxf_parser.parse(dxf_path)
    if ext == ".slddrw":
        from . import swx_parser
        return swx_parser.parse(path)
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"):
        from . import image_parser
        return image_parser.parse(path)

    raise ValueError(f"未対応の拡張子: {ext}")
