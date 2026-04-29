# -*- coding: utf-8 -*-
"""
図枠・タイトルブロックの記入漏れチェック

ロジック：
1. ページサイズからA0〜A4を判定
2. ページ右下領域のテキストを抽出してタイトルブロック領域を推定
3. 各フィールド（図番・品名・材質・尺度・投影法・設計者・日付等）の記入有無を判定
4. 第三角法マークの有無をチェック（キーワード＋近傍記号）
"""
from __future__ import annotations

import re

from ..model import BBox, CheckReport, Drawing, Finding, Page, Severity, TitleBlock
from ..utils.logger import get_logger
from .base import BaseChecker

logger = get_logger(__name__)


# タイトルブロックがあると想定する領域：ページ右下の一定範囲
TITLE_BLOCK_AREA_RATIO = 0.35   # ページ長辺のこの割合だけ右下から


class TitleBlockChecker(BaseChecker):
    name = "title_block_checker"

    def check(self, drawing: Drawing, report: CheckReport) -> None:
        for page in drawing.pages:
            self._check_page(page, drawing, report)

    # ------------------------------------------------------------------
    def _check_page(self, page: Page, drawing: Drawing, report: CheckReport) -> None:
        # 1. 用紙サイズ判定（記録のみ。非JIS用紙でも警告はしない＝実務では自由に使うため）
        if drawing.source_format in ("pdf", "image"):
            page.sheet_size = self.rules.get_sheet_size_from_dimensions(page.width, page.height)

        # 2. タイトルブロック領域のテキスト抽出
        title_block = self._extract_title_block(page)
        page.title_block = title_block

        # 3. 各必須フィールドの記入チェック
        self._check_required_fields(page, title_block, report)

        # 4. 第三角法マークのチェックは廃止（JIS教科書的指摘のため）

    # ------------------------------------------------------------------
    def _extract_title_block(self, page: Page) -> TitleBlock:
        """
        タイトルブロック抽出（実装変更）

        【以前の問題】
        「ページ右下領域」を座標で決め打ちしていたが、SolidWorksのPDFは
        ページ回転・中心オフセットなどで座標系が不定。誤検知の原因だった。

        【新方式】
        領域は使わず、ページ全文テキストに「図番」「品名」等のキーワードが
        何件ヒットするかでタイトルブロックの充実度を判定する。
        """
        w, h = page.width, page.height
        tb = TitleBlock(sheet_size=page.sheet_size)

        all_text = page.raw_text or ""
        tb_texts: list[tuple[BBox, str]] = [
            (ent.bbox, ent.text)
            for ent in page.entities
            if ent.type.value == "text"
        ]

        # 各フィールドのキーワードマッチで値を拾う（領域に依存しない）
        fields_def = self.rules.title_block_fields()
        for fdef in fields_def:
            key = fdef["key"]
            keywords = fdef.get("keywords_ja", [])
            value = self._find_field_value(tb_texts, all_text, keywords, fdef.get("pattern"))
            if value:
                tb.fields[key] = value
            elif fdef.get("required"):
                tb.missing_fields.append(key)

        return tb

    def _in_area(self, bbox: BBox, area: BBox) -> bool:
        cx, cy = bbox.center
        return area.x0 <= cx <= area.x1 and area.y0 <= cy <= area.y1

    def _find_field_value(
        self,
        tb_texts: list[tuple[BBox, str]],
        all_text: str,
        keywords: list[str],
        pattern: str | None,
    ) -> str | None:
        """
        タイトルブロックのラベルと値が別セルに分かれている書式に対応。
        スペース等で分断された表記揺れ（「図  番」「Drawing No.」等）も許容する。

        判定の流れ：
        1. ラベルキーワードが、どのテキスト中にも（空白無視で）含まれれば
           「そのフィールドは記入あり」とみなす（緩め判定）
        2. 可能なら隣接テキストから値を拾うが、拾えなくてもOK
        """
        def _normalize(s: str) -> str:
            return re.sub(r"\s+", "", s).lower()

        all_text_norm = _normalize(all_text)

        for kw in keywords:
            kw_norm = _normalize(kw)
            if not kw_norm:
                continue

            # --- ラベルの存在判定（空白無視）
            label_entity = None
            for bbox, text in tb_texts:
                if kw_norm in _normalize(text):
                    label_entity = (bbox, text)
                    break

            if label_entity is None and kw_norm not in all_text_norm:
                continue  # このキーワードはマッチせず、次のキーワードへ

            # --- ラベルの隣接テキストから値を拾う（できればで十分）
            if label_entity is not None:
                bbox, text = label_entity
                cx, cy = bbox.center
                # 同一テキスト内に値が含まれているケース（例: "図番: A123"）
                m = re.search(
                    rf"{re.escape(kw)}\s*[:：]?\s*(\S.+?)$",
                    text,
                )
                if m and m.group(1).strip() and _normalize(m.group(1)) != kw_norm:
                    candidate = m.group(1).strip()
                    if not pattern or re.search(pattern, candidate):
                        return candidate
                # 隣接セル（右側）
                for b2, t2 in tb_texts:
                    if b2 is bbox:
                        continue
                    if _normalize(t2) == kw_norm:
                        continue
                    c2x, c2y = b2.center
                    if abs(c2y - cy) < 15 and c2x > cx + 5:
                        candidate = t2.strip()
                        if candidate:
                            if not pattern or re.search(pattern, candidate):
                                return candidate
                # 隣接セル（下側 = PDF座標でy小さい方）
                for b2, t2 in tb_texts:
                    if b2 is bbox:
                        continue
                    if _normalize(t2) == kw_norm:
                        continue
                    c2x, c2y = b2.center
                    if abs(c2x - cx) < 40 and c2y < cy - 3 and (cy - c2y) < 30:
                        candidate = t2.strip()
                        if candidate:
                            if not pattern or re.search(pattern, candidate):
                                return candidate

            # 値は拾えなかったが、ラベルが存在するので「記入あり」とみなす（緩判定）
            return f"(ラベル「{kw}」検出)"

        return None

    # ------------------------------------------------------------------
    def _check_required_fields(
        self, page: Page, tb: TitleBlock, report: CheckReport
    ) -> None:
        """
        【方針】
        キーワードベースで必須フィールドの有無を判定する。
        ただし社内フォーマットの表記揺れで誤検知が出るのを抑えるため、
        「主要フィールド（図番/品名/材質/尺度）のうち複数が全く見つからない場合」のみ
        ERROR を出す。1〜2個の欠落は表記揺れの可能性が高いので指摘しない。

        社内フォーマットを学習させると、より正確になる（learned_rules.json）。
        """
        critical_keys = {"drawing_number", "part_name", "material", "scale"}
        critical_missing = [k for k in tb.missing_fields if k in critical_keys]

        # 主要フィールドが3つ以上欠落 → タイトルブロックが白紙に近い可能性
        if len(critical_missing) >= 3:
            field_labels = {
                "drawing_number": "図番",
                "part_name": "品名",
                "material": "材質",
                "scale": "尺度",
            }
            missing_labels = [field_labels.get(k, k) for k in critical_missing]
            report.add(
                Finding(
                    checker=self.name,
                    rule_id="TITLE-BLOCK-EMPTY",
                    severity=Severity.ERROR,
                    message=f"タイトルブロックに {'、'.join(missing_labels)} の記入が確認できません。",
                    page_number=page.page_number,
                    bbox=None,
                    suggestion="タイトルブロックの記入を確認。社内フォーマット固有の表記は「サンプル学習」で認識精度が向上します",
                    jis_reference="JIS Z 8310",
                )
            )

    def _rule_by_field_key(self, field_key: str) -> dict | None:
        for r in self.my_rules():
            if r.get("field_key") == field_key:
                return r
        return None

    # ------------------------------------------------------------------
    def _check_blank_page(self, page: Page, report: CheckReport) -> None:
        rule = self.rules.get_rule("FALLBACK-001")
        if rule is None:
            return
        min_count = self.rules.settings.get("min_entities_per_page", 5)
        if len(page.entities) < min_count:
            report.add(
                Finding(
                    checker=self.name,
                    rule_id=rule["id"],
                    severity=Severity(rule.get("severity", "error")),
                    message=f"ページに含まれるエンティティ数が{len(page.entities)}と少なく、空白図面の可能性があります。",
                    page_number=page.page_number,
                    bbox=None,
                    suggestion="内容が正しいか確認",
                )
            )
