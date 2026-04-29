# -*- coding: utf-8 -*-
"""チェッカーの基底クラス"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..model import CheckReport, Drawing

if TYPE_CHECKING:
    from ..rule_engine import RuleEngine


class BaseChecker(ABC):
    """すべてのチェッカーが継承する基底"""

    name: str = "base_checker"

    def __init__(self, rule_engine: "RuleEngine"):
        self.rules = rule_engine

    @abstractmethod
    def check(self, drawing: Drawing, report: CheckReport) -> None:
        """検図を実行し、見つかった不備をreportに追加する"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 共通ヘルパー
    # ------------------------------------------------------------------
    def my_rules(self) -> list[dict]:
        return self.rules.rules_for_checker(self.name)
