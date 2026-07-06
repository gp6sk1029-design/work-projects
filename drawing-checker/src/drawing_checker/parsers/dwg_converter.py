# -*- coding: utf-8 -*-
"""
DWG→DXF変換（ODA File Converter のCLIラッパー）

ODA File Converter は無償でダウンロード可能：
  https://www.opendesign.com/guestfiles/oda_file_converter

.env の ODA_CONVERTER_PATH に実行ファイルパスを設定する。
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)


def convert_to_dxf(dwg_path: Path) -> Path:
    """DWGファイルをDXFに変換し、変換後のDXFパスを返す"""
    oda_path = os.environ.get("ODA_CONVERTER_PATH", "")
    if not oda_path or not Path(oda_path).exists():
        raise FileNotFoundError(
            "ODA File Converter が見つかりません。"
            ".env の ODA_CONVERTER_PATH を正しく設定してください。"
        )

    # ODA File Converter は入力ディレクトリと出力ディレクトリを指定する
    # そのため、一時ディレクトリを用意してそこに dwg をコピーしてから変換する
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        input_dir = Path(tmp_in)
        output_dir = Path(tmp_out)

        target = input_dir / dwg_path.name
        target.write_bytes(dwg_path.read_bytes())

        # CLI引数:
        #   入力dir 出力dir 出力バージョン 出力フォーマット 再帰 監査
        # 出力バージョン例: ACAD2018, ACAD2013, ACAD2010
        # 出力フォーマット: DXF
        cmd = [
            oda_path,
            str(input_dir),
            str(output_dir),
            "ACAD2018",
            "DXF",
            "0",  # 再帰=0
            "1",  # 監査=1
        ]
        logger.info("ODA File Converter 実行: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.warning("ODA 変換が非ゼロで終了: stderr=%s", result.stderr)

        # 出力DXFを作業一時ディレクトリから、永続化できる場所（DWG隣）に移す
        dxf_candidates = list(output_dir.glob("*.dxf"))
        if not dxf_candidates:
            raise RuntimeError("ODA変換後のDXFが見つかりません")

        dst = dwg_path.with_suffix(".dxf")
        dst.write_bytes(dxf_candidates[0].read_bytes())
        return dst
