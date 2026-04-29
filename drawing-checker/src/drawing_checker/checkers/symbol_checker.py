# -*- coding: utf-8 -*-
"""
記号チェック（学習ベース・最小構成）

【方針】
「表面性状が無いから指摘」「旧▽記号」のようなJIS教科書的指摘は廃止。
記号が実際に使われている場合にのみ、構造的な不備をチェックする。

  ○ 幾何公差フレームに公差値が無い（明らかな記入漏れ）
  ○ 幾何公差で参照されているデータムが図面上に無い
  ○ 「溶接」等のキーワードがあるのに溶接記号が見当たらない
"""
from __future__ import annotations

import re

from ..model import CheckReport, Drawing, Finding, Severity
from ..utils.logger import get_logger
from .base import BaseChecker

logger = get_logger(__name__)


# 幾何公差の特性記号
GEOMETRIC_SYMBOLS = [
    "⏤", "⏥", "○", "⌭", "⌒", "⌓",
    "∥", "⊥", "∠",
    "◎", "⌖", "↗", "⌯",
]

# 幾何公差フレーム内のパターン（記号｜値｜データム）
GEOM_FRAME_PATTERN = re.compile(
    r"(?P<sym>[⏤⏥○⌭⌒⌓∥⊥∠◎⌖↗⌯])\s*"
    r"(?P<val>φ?\s*[\d.]+)?\s*"
    r"(?P<datum>[A-Z](?:\s+[A-Z]){0,2})?"
)

# データム指示
DATUM_DEF_PATTERN = re.compile(r"データム\s*([A-Z])|(?:^|\s)([A-Z])\s*$", re.MULTILINE)

# 溶接記号
WELDING_SYMBOLS = ["▷", "△", "▽", "□", "V", "Y", "U", "J", "X", "K"]


class SymbolChecker(BaseChecker):
    name = "symbol_checker"

    def check(self, drawing: Drawing, report: CheckReport) -> None:
        for page in drawing.pages:
            text = page.raw_text or ""
            self._check_geometric_tolerance(page, text, report)
            self._check_welding(page, text, report)
            self._check_datum_consistency(page, text, report)

    # ------------------------------------------------------------------
    def _check_geometric_tolerance(self, page, text: str, report: CheckReport) -> None:
        """JIS B 0021-001：幾何公差フレームの3要素（記号｜値｜データム）"""
        if not any(s in text for s in GEOMETRIC_SYMBOLS):
            return
        rule = self.rules.get_rule("JIS-B-0021-001")
        for m in GEOM_FRAME_PATTERN.finditer(text):
            val = (m.group("val") or "").strip()
            if not val:
                report.add(
                    Finding(
                        checker=self.name,
                        rule_id=(rule or {}).get("id", "GEOM-VALUE-MISSING"),
                        severity=Severity.ERROR,
                        message=f"幾何公差フレーム「{m.group(0)}」に公差値がありません。",
                        page_number=page.page_number,
                        bbox=None,
                        suggestion="公差値を記入（例：0.05）",
                        jis_reference=(rule or {}).get("jis_reference", "JIS B 0021"),
                    )
                )

    # ------------------------------------------------------------------
    def _check_welding(self, page, text: str, report: CheckReport) -> None:
        """JIS Z 3021-001：溶接キーワードがあるのに溶接記号が見当たらない"""
        if not any(kw in text for kw in ["溶接", "weld", "WELD", "すみ肉", "突合せ"]):
            return
        if any(s in text for s in WELDING_SYMBOLS):
            return
        rule = self.rules.get_rule("JIS-Z-3021-001")
        report.add(
            Finding(
                checker=self.name,
                rule_id=(rule or {}).get("id", "WELD-SYMBOL-MISSING"),
                severity=Severity.WARNING,
                message="溶接に関する記述がありますが、溶接記号が見当たりません。",
                page_number=page.page_number,
                bbox=None,
                suggestion="溶接部に基本記号（すみ肉△、突合せV等）を記入",
                jis_reference=(rule or {}).get("jis_reference", "JIS Z 3021"),
            )
        )

    # ------------------------------------------------------------------
    def _check_datum_consistency(self, page, text: str, report: CheckReport) -> None:
        """JIS B 0021-002：幾何公差で参照されているデータム記号が図面上に定義されているか"""
        referenced: set[str] = set()
        for m in GEOM_FRAME_PATTERN.finditer(text):
            datum_str = (m.group("datum") or "").strip()
            for d in re.split(r"\s+", datum_str):
                if d and d.isalpha() and len(d) == 1:
                    referenced.add(d.upper())
        if not referenced:
            return

        defined: set[str] = set()
        for m in DATUM_DEF_PATTERN.finditer(text):
            d = m.group(1) or m.group(2)
            if d:
                defined.add(d.upper())

        rule = self.rules.get_rule("JIS-B-0021-002")
        missing = referenced - defined
        for d in sorted(missing):
            report.add(
                Finding(
                    checker=self.name,
                    rule_id=(rule or {}).get("id", "DATUM-UNDEFINED"),
                    severity=Severity.ERROR,
                    message=f"幾何公差で参照されているデータム「{d}」が図面上に定義されていません。",
                    page_number=page.page_number,
                    bbox=None,
                    suggestion=f"該当形体にデータム記号「{d}」を追加",
                    jis_reference=(rule or {}).get("jis_reference", "JIS B 0021"),
                )
            )
