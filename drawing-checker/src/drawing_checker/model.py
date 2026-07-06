# -*- coding: utf-8 -*-
"""
統一ドローイングモデル

PDF / DXF / DWG / SLDDRW / PNG/JPG の各パーサーから得た情報を、
共通のデータ構造に正規化する。
全チェッカーはこのモデルを入力として動作する。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    """検図結果の重大度"""
    ERROR = "error"        # 赤：必須修正
    WARNING = "warning"    # 黄：要確認
    INFO = "info"          # 青：助言


class EntityType(str, Enum):
    """図面エンティティの種類"""
    LINE = "line"
    POLYLINE = "polyline"
    CIRCLE = "circle"
    ARC = "arc"
    ELLIPSE = "ellipse"
    TEXT = "text"
    DIMENSION = "dimension"
    LEADER = "leader"
    HATCH = "hatch"
    BLOCK = "block"
    SYMBOL = "symbol"
    UNKNOWN = "unknown"


class LineStyle(str, Enum):
    """線種（JIS Z 8114準拠）"""
    CONTINUOUS = "continuous"       # 実線（外形線）
    HIDDEN = "hidden"               # 破線（隠れ線）
    CENTER = "center"               # 一点鎖線（中心線）
    PHANTOM = "phantom"             # 二点鎖線（想像線）
    DIMENSION = "dimension"         # 寸法線・引出線
    UNKNOWN = "unknown"


@dataclass
class BBox:
    """バウンディングボックス（PDFページ座標系：左下原点、単位pt）"""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


@dataclass
class Entity:
    """図面エンティティ（線・円・文字・寸法などの汎用表現）"""
    type: EntityType
    bbox: BBox
    layer: str = ""                 # DXF由来：レイヤー名
    line_style: LineStyle = LineStyle.UNKNOWN
    line_width: float = 0.0         # pt
    color: str = "#000000"
    text: str = ""                  # TEXT/DIMENSIONの場合の文字列
    raw: dict[str, Any] = field(default_factory=dict)  # 元パーサーの生データ


@dataclass
class Dimension:
    """寸法エンティティ（専用型で詳細を持つ）"""
    bbox: BBox
    value: str                      # 寸法値文字列（例："φ25H7"）
    numeric_value: Optional[float] = None  # 数値化できる場合
    tolerance: Optional[str] = None        # 公差記号（例："H7", "±0.1"）
    is_diameter: bool = False       # φ付き
    is_radius: bool = False         # R付き
    reference_entity_id: Optional[int] = None  # 参照先エンティティ
    layer: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TitleBlock:
    """タイトルブロック（図枠の情報欄）"""
    bbox: Optional[BBox] = None
    fields: dict[str, str] = field(default_factory=dict)
    # キー例：drawing_number, part_name, material, scale, projection,
    #         designer, checker, approver, date, revision
    missing_fields: list[str] = field(default_factory=list)
    sheet_size: str = ""            # A4, A3, A2, A1, A0


@dataclass
class Symbol:
    """表面粗さ・幾何公差・溶接記号など"""
    type: str                       # "surface_roughness", "geometric_tolerance", "welding", "datum"
    bbox: BBox
    raw_text: str = ""
    parsed: dict[str, Any] = field(default_factory=dict)
    # 幾何公差例: {"symbol": "⊥", "value": "0.05", "datum": "A"}
    # 表面粗さ例: {"ra": "1.6"}
    # 溶接例:     {"type": "fillet", "size": "6"}


@dataclass
class Page:
    """1ページ分のデータ"""
    page_number: int
    width: float                    # pt
    height: float                   # pt
    sheet_size: str = ""            # A4, A3等
    entities: list[Entity] = field(default_factory=list)
    dimensions: list[Dimension] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    title_block: Optional[TitleBlock] = None
    raw_text: str = ""              # 全文テキスト


@dataclass
class Drawing:
    """図面全体の統一表現"""
    source_path: str
    source_format: str              # "pdf", "dxf", "dwg", "slddrw", "image"
    pages: list[Page] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    """検図結果の1件"""
    checker: str                    # "dimension_checker" などのチェッカー名
    rule_id: str                    # "DIM001" などのルールID
    severity: Severity
    message: str                    # 日本語の指摘コメント
    page_number: int = 1
    bbox: Optional[BBox] = None     # 指摘箇所の座標（PDFマーキング用）
    suggestion: str = ""            # 修正提案
    jis_reference: str = ""         # 根拠JIS規格番号（例："JIS B 0405"）

    def to_dict(self) -> dict[str, Any]:
        return {
            "checker": self.checker,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "page_number": self.page_number,
            "bbox": {
                "x0": self.bbox.x0, "y0": self.bbox.y0,
                "x1": self.bbox.x1, "y1": self.bbox.y1,
            } if self.bbox else None,
            "suggestion": self.suggestion,
            "jis_reference": self.jis_reference,
        }


@dataclass
class CheckReport:
    """検図結果全体"""
    drawing_path: str
    findings: list[Finding] = field(default_factory=list)
    processing_time_sec: float = 0.0
    errors_count: int = 0
    warnings_count: int = 0
    info_count: int = 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)
        if finding.severity == Severity.ERROR:
            self.errors_count += 1
        elif finding.severity == Severity.WARNING:
            self.warnings_count += 1
        else:
            self.info_count += 1

    @property
    def is_pass(self) -> bool:
        """ERROR がゼロなら合格"""
        return self.errors_count == 0
