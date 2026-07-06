# -*- coding: utf-8 -*-
"""
線種チェック（学習ベース・最小構成）

【方針】
JIS規格の線幅/線種チェックはすべて廃止。誤検知が多く実務で役に立たなかったため。
現時点ではDXFのレイヤーに線種の混在があった場合のみ指摘する。
社内固有の線種ルールはサンプル学習（learned_rules.json）で補完する想定。
"""
from __future__ import annotations

from ..model import CheckReport, Drawing, EntityType, Finding, Severity
from ..utils.logger import get_logger
from .base import BaseChecker

logger = get_logger(__name__)


class LineStyleChecker(BaseChecker):
    name = "line_style_checker"

    def check(self, drawing: Drawing, report: CheckReport) -> None:
        if drawing.source_format != "dxf":
            return
        for page in drawing.pages:
            self._check_layer_mix(page, report)

    def _check_layer_mix(self, page, report: CheckReport) -> None:
        """同一レイヤーに複数の線種が混ざっている場合のみ警告"""
        layer_styles: dict[str, set[str]] = {}
        for ent in page.entities:
            if ent.type not in (EntityType.LINE, EntityType.POLYLINE):
                continue
            layer = ent.layer or ""
            if not layer:
                continue
            style = ent.line_style.value
            if style == "unknown":
                continue
            layer_styles.setdefault(layer, set()).add(style)

        for layer, styles in layer_styles.items():
            if len(styles) > 1:
                report.add(
                    Finding(
                        checker=self.name,
                        rule_id="LAYER-MIX",
                        severity=Severity.WARNING,
                        message=f"レイヤー「{layer}」に複数の線種（{', '.join(sorted(styles))}）が混在しています。",
                        page_number=page.page_number,
                        bbox=None,
                        suggestion="線種ごとにレイヤーを分ける",
                    )
                )
