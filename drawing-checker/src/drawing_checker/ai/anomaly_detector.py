# -*- coding: utf-8 -*-
"""
Gemini AI を使って、ルールベースで拾えない違和感を検出するレイヤー。

入力：Drawing オブジェクトの軽量サマリ（テキスト中心）
出力：Finding のリスト（追加指摘として CheckReport に追記）
"""
from __future__ import annotations

import json
from typing import Optional

from ..model import CheckReport, Drawing, Finding, Severity
from ..utils.logger import get_logger
from .gemini_client import GeminiClient

logger = get_logger(__name__)


def run(drawing: Drawing, report: CheckReport) -> None:
    """既存の report に AI 指摘を追加する"""
    client = GeminiClient()
    if not client.available:
        return

    summary = _build_summary(drawing)
    prompt = f"""あなたはJIS準拠の機械設計図面の検図専門家です。
以下は検図対象の図面サマリーです。

```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

図面全体を俯瞰して、以下の観点から「人間が見たら気付く違和感」を検出してください。
- 寸法・公差・記号の使い方の不自然さ
- 情報の欠落（人が作業するときに困る情報）
- JIS規格に沿っていない表記ゆれ
- 意図が曖昧な注記や記号

結果は以下のJSON配列で返してください。指摘がなければ空配列 [] を返してください。
各指摘は短く具体的に。憶測や過剰な指摘は避けてください。

```json
[
  {{
    "severity": "error|warning|info",
    "page_number": 1,
    "message": "指摘内容（日本語、80文字以内）",
    "suggestion": "修正提案（日本語、40文字以内）"
  }}
]
```
"""
    findings = client.generate_json(prompt, temperature=0.2)
    if not isinstance(findings, list):
        return

    for f in findings:
        if not isinstance(f, dict):
            continue
        sev_str = (f.get("severity") or "info").lower()
        try:
            sev = Severity(sev_str)
        except ValueError:
            sev = Severity.INFO
        report.add(
            Finding(
                checker="ai_anomaly_detector",
                rule_id="AI-001",
                severity=sev,
                message=str(f.get("message") or "")[:200],
                page_number=int(f.get("page_number") or 1),
                bbox=None,
                suggestion=str(f.get("suggestion") or "")[:120],
                jis_reference="",
            )
        )


def _build_summary(drawing: Drawing) -> dict:
    """AIに渡す軽量サマリ"""
    return {
        "source_format": drawing.source_format,
        "page_count": len(drawing.pages),
        "pages": [
            {
                "page_number": p.page_number,
                "sheet_size": p.sheet_size,
                "entity_count": len(p.entities),
                "dimension_count": len(p.dimensions),
                "dimensions_sample": [
                    {"value": d.value, "tolerance": d.tolerance,
                     "is_diameter": d.is_diameter, "is_radius": d.is_radius}
                    for d in p.dimensions[:30]
                ],
                "title_block_fields": (
                    p.title_block.fields if p.title_block else {}
                ),
                "title_block_missing": (
                    p.title_block.missing_fields if p.title_block else []
                ),
                "text_preview": p.raw_text[:1500],
            }
            for p in drawing.pages
        ],
    }
