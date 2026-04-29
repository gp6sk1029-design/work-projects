# -*- coding: utf-8 -*-
"""
寸法チェック（JIS準拠・実務向けに絞り込んだ版）

【方針】
JISルールを参照情報として付加しつつ、誤検知が多かった検査は無効化する。
残すのは以下：
  ○ 寸法が1つも検出されない（JIS Z 8317-001）
  ○ 単位ミス疑い（10000mm超）
"""
from __future__ import annotations

from ..model import (
    CheckReport,
    Dimension,
    Drawing,
    EntityType,
    Finding,
    Severity,
)
from ..utils.geometry import unify_bbox
from ..utils.logger import get_logger
from .base import BaseChecker

logger = get_logger(__name__)


class DimensionChecker(BaseChecker):
    name = "dimension_checker"

    def check(self, drawing: Drawing, report: CheckReport) -> None:
        for page in drawing.pages:
            self._check_no_dimensions(page, report)
            self._check_unusual_values(page.dimensions, report, page.page_number)

    # ------------------------------------------------------------------
    def _check_no_dimensions(self, page, report: CheckReport) -> None:
        """JIS Z 8317-001：寸法が1つも無い図面は致命的"""
        rule = self.rules.get_rule("JIS-Z-8317-001")
        shape_types = {
            EntityType.CIRCLE,
            EntityType.ARC,
            EntityType.POLYLINE,
            EntityType.LINE,
        }
        shapes = [e for e in page.entities if e.type in shape_types]
        if not shapes or page.dimensions:
            return

        bbox_all = unify_bbox([e.bbox for e in shapes])
        report.add(
            Finding(
                checker=self.name,
                rule_id=(rule or {}).get("id", "DIM-NO-DIMENSIONS"),
                severity=Severity.ERROR,
                message="寸法が1つも記入されていません。",
                page_number=page.page_number,
                bbox=bbox_all,
                suggestion="主要形状に寸法記入を追加",
                jis_reference=(rule or {}).get("jis_reference", "JIS Z 8317"),
            )
        )

    # ------------------------------------------------------------------
    def _check_unusual_values(
        self, dims: list[Dimension], report: CheckReport, page_number: int
    ) -> None:
        """単位ミスが疑われる異常な寸法値"""
        for d in dims:
            if d.numeric_value is None:
                continue
            if d.numeric_value > 10000:
                report.add(
                    Finding(
                        checker=self.name,
                        rule_id="DIM-UNIT-SUSPECT",
                        severity=Severity.WARNING,
                        message=f"寸法値「{d.value}」が10000mmを超えています。単位ミスの可能性があります。",
                        page_number=page_number,
                        bbox=d.bbox,
                        suggestion="寸法値と単位を再確認",
                    )
                )
