# -*- coding: utf-8 -*-
"""
SolidWorks 図面（.slddrw）パーサー

SolidWorks COM API を使って図面を開き、アノテーション・寸法・注記を取得する。
- SolidWorks 本体がインストールされた Windows PC でのみ動作
- 未インストール時は簡潔なエラーを返してフォールバック可能にする

代替運用（推奨）：
- SolidWorks 側で SLDDRW を PDF 出力 → 本ツールの PDF パーサーに流す
"""
from __future__ import annotations

import platform
from pathlib import Path

from ..model import BBox, Dimension, Drawing, Entity, EntityType, Page
from ..utils.logger import get_logger

logger = get_logger(__name__)


def parse(path: str | Path) -> Drawing:
    path = Path(path)
    if platform.system() != "Windows":
        raise RuntimeError(
            "SolidWorks (.slddrw) 解析は Windows + SolidWorks インストール環境でのみ動作します。"
        )
    try:
        import win32com.client  # type: ignore
    except ImportError as e:
        raise ImportError(
            "pywin32 が未インストールです。pip install pywin32 を実行してください。"
        ) from e

    try:
        sw_app = win32com.client.Dispatch("SldWorks.Application")
    except Exception as e:
        raise RuntimeError(
            "SolidWorks Application の起動に失敗しました。SolidWorks がインストールされているか確認してください。"
        ) from e

    sw_app.Visible = False
    drawings_result: list[Page] = []

    # 図面を開く（読み取り専用）
    errors = 0
    warnings = 0
    try:
        model = sw_app.OpenDoc6(
            str(path),
            3,           # swDocDRAWING = 3
            1,           # swOpenDocOptions_Silent = 1
            "",
            errors,
            warnings,
        )
        if model is None:
            raise RuntimeError("SolidWorks 図面のオープンに失敗しました")

        drawing_doc = model
        sheets = drawing_doc.GetSheetNames()
        for sheet_index, sheet_name in enumerate(sheets or []):
            drawing_doc.ActivateSheet(sheet_name)
            sheet = drawing_doc.IGetCurrentSheet()

            entities: list[Entity] = []
            dimensions: list[Dimension] = []
            raw_texts: list[str] = []

            # 寸法・注記収集（View単位で走査）
            view = drawing_doc.GetFirstView()
            # 最初のビューはシート全体、次からが各ビュー
            while view is not None:
                # 注記（Note）
                note = view.GetFirstNote()
                while note is not None:
                    try:
                        text = note.GetText() or ""
                        if text.strip():
                            raw_texts.append(text)
                            entities.append(
                                Entity(
                                    type=EntityType.TEXT,
                                    bbox=BBox(0, 0, 0, 0),
                                    text=text,
                                    raw={"source": "sw_note"},
                                )
                            )
                    except Exception:
                        pass
                    note = note.GetNext()

                # 寸法
                disp_dim = view.GetFirstDisplayDimension5()
                while disp_dim is not None:
                    try:
                        dim_obj = disp_dim.GetDimension2(0)
                        value_text = dim_obj.FullText if hasattr(dim_obj, "FullText") else ""
                        value_num = None
                        try:
                            value_num = float(dim_obj.Value)
                        except Exception:
                            pass
                        dimensions.append(
                            Dimension(
                                bbox=BBox(0, 0, 0, 0),
                                value=value_text or "",
                                numeric_value=value_num,
                            )
                        )
                    except Exception:
                        pass
                    disp_dim = disp_dim.GetNext5()

                view = view.GetNextView()

            drawings_result.append(
                Page(
                    page_number=sheet_index + 1,
                    width=1000.0,
                    height=1000.0,
                    entities=entities,
                    dimensions=dimensions,
                    raw_text="\n".join(raw_texts),
                )
            )
    finally:
        try:
            sw_app.CloseDoc(path.name)
        except Exception:
            pass

    return Drawing(
        source_path=str(path),
        source_format="slddrw",
        pages=drawings_result or [Page(page_number=1, width=1000, height=1000)],
    )
