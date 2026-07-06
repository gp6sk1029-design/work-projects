# -*- coding: utf-8 -*-
"""
ルール合成エンジン（3層構造）

優先順位：
  [1] learned_rules.json  （サンプル図面から学習）← 最優先
  [2] jis_rules.json      （JIS規格を事前内蔵）
  [3] check_rules.json    （汎用フォールバック）

同一ルールIDが複数層にある場合、上位の層が勝つ。
jis_rules.json で override_by_sample: false のルールは
サンプル学習で上書き不可（JIS必須項目の保全）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


class RuleEngine:
    """検図ルールの読み込み・合成・引き当て"""

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        custom_rules_path: Optional[Path] = None,
    ):
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self.custom_rules_path = custom_rules_path

        self.jis_rules: list[dict[str, Any]] = []
        self.learned_rules: list[dict[str, Any]] = []
        self.fallback_rules: list[dict[str, Any]] = []
        self.tolerance_table: dict[str, Any] = {}
        self.title_block_templates: dict[str, Any] = {}
        self.settings: dict[str, Any] = {}

        self._load_all()

    # ------------------------------------------------------------------
    # 読み込み
    # ------------------------------------------------------------------
    def _load_json(self, path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default if default is not None else {}
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def _load_all(self) -> None:
        jis = self._load_json(self.config_dir / "jis_rules.json", {"rules": []})
        self.jis_rules = jis.get("rules", [])

        fb = self._load_json(self.config_dir / "check_rules.json", {"rules": [], "settings": {}})
        self.fallback_rules = fb.get("rules", [])
        self.settings = fb.get("settings", {})

        learned_path = (
            self.custom_rules_path
            if self.custom_rules_path
            else self.config_dir / "learned_rules.json"
        )
        learned = self._load_json(learned_path, {"rules": []})
        self.learned_rules = learned.get("rules", [])

        self.tolerance_table = self._load_json(
            self.config_dir / "tolerance_table.json", {}
        )
        self.title_block_templates = self._load_json(
            self.config_dir / "title_block_templates.json", {}
        )

    # ------------------------------------------------------------------
    # 合成
    # ------------------------------------------------------------------
    def effective_rules(self) -> list[dict[str, Any]]:
        """
        3層をマージした有効ルール一覧を返す。
        learned > JIS > fallback の優先順位。
        JIS で override_by_sample: false のルールは learned で上書き不可。
        """
        merged: dict[str, dict[str, Any]] = {}

        # 1. JIS（ベース）
        for rule in self.jis_rules:
            merged[rule["id"]] = dict(rule)

        # 2. learned（上書き可能なもののみ）
        for rule in self.learned_rules:
            rid = rule["id"]
            if rid in merged:
                if merged[rid].get("override_by_sample", True):
                    merged[rid] = {**merged[rid], **rule}
            else:
                merged[rid] = dict(rule)

        # 3. fallback（未登録のみ）
        for rule in self.fallback_rules:
            rid = rule["id"]
            if rid not in merged:
                merged[rid] = dict(rule)

        return list(merged.values())

    @property
    def has_learned_rules(self) -> bool:
        return len(self.learned_rules) > 0

    # ------------------------------------------------------------------
    # 引き当て
    # ------------------------------------------------------------------
    def rules_for_checker(self, checker_name: str) -> list[dict[str, Any]]:
        """特定チェッカーに紐づくルールだけを返す"""
        return [
            r for r in self.effective_rules()
            if r.get("checker") == checker_name
        ]

    def get_rule(self, rule_id: str) -> Optional[dict[str, Any]]:
        for r in self.effective_rules():
            if r["id"] == rule_id:
                return r
        return None

    def get_general_tolerance(self, size: float) -> Optional[float]:
        """JIS B 0405 中級の普通公差値（mm）を寸法値から引き当て"""
        gt = self.tolerance_table.get("general_tolerance", {})
        for r in gt.get("ranges", []):
            if r["size_min"] < size <= r["size_max"]:
                return r["tolerance"]
        return None

    def get_it_tolerance_um(self, size: float, grade: str) -> Optional[float]:
        """IT等級（IT5〜IT12）の公差値（μm）を寸法値から引き当て"""
        it = self.tolerance_table.get("it_grades", {})
        grade_key = grade.upper() if not grade.upper().startswith("IT") else grade.upper()
        for r in it.get("ranges", []):
            if r["size_min"] < size <= r["size_max"]:
                return r.get("values", {}).get(grade_key)
        return None

    def get_sheet_size_from_dimensions(
        self, width_pt: float, height_pt: float, tol_pct: float = 0.05
    ) -> str:
        """ページ寸法（pt）から JIS 用紙サイズ（A0〜A4）を推定"""
        sizes = self.title_block_templates.get("sheet_sizes", {})
        long_side = max(width_pt, height_pt)
        short_side = min(width_pt, height_pt)
        for name, spec in sizes.items():
            w = spec["width_pt"]
            h = spec["height_pt"]
            l = max(w, h)
            s = min(w, h)
            if (abs(long_side - l) / l <= tol_pct
                    and abs(short_side - s) / s <= tol_pct):
                return name
        return ""

    def title_block_fields(self) -> list[dict[str, Any]]:
        """標準タイトルブロックのフィールド定義を返す"""
        return self.title_block_templates.get("title_block_default", {}).get("fields", [])

    def annotation_color(self, severity: str) -> str:
        """重大度に対応する注釈色（hex）"""
        colors = self.settings.get("annotation_colors", {})
        return colors.get(severity, "#FF0000")

    def annotation_radius(self) -> float:
        """PDF注釈のマーカー半径（pt）"""
        return self.settings.get("annotation_marker_radius_pt", 12)
