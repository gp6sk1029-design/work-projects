# -*- coding: utf-8 -*-
"""検図結果をHTMLサマリレポートに出力"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Optional

from ..model import CheckReport, Severity


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>検図レポート - {filename}</title>
<style>
  body {{ font-family: "Meiryo UI", sans-serif; margin: 24px; color: #222; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 8px; }}
  .summary {{ display: flex; gap: 16px; margin: 16px 0; }}
  .chip {{ padding: 8px 16px; border-radius: 6px; font-weight: bold; }}
  .chip.error {{ background: #ffe6e6; color: #c00; }}
  .chip.warning {{ background: #fff3e0; color: #b36b00; }}
  .chip.info {{ background: #e6f0ff; color: #0057b3; }}
  .chip.pass {{ background: #e6ffed; color: #148c3d; }}
  .chip.fail {{ background: #ffe6e6; color: #c00; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
  th, td {{ border: 1px solid #ccc; padding: 8px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #f4f4f4; }}
  tr.error {{ background: #fff5f5; }}
  tr.warning {{ background: #fffaf0; }}
  tr.info {{ background: #f5f9ff; }}
  .rule-id {{ font-family: monospace; color: #555; }}
  .jis {{ color: #666; font-size: 0.9em; }}
  .suggestion {{ color: #0a7a0a; font-size: 0.95em; margin-top: 4px; }}
</style>
</head>
<body>
  <h1>検図レポート</h1>
  <p><strong>対象:</strong> {filepath}</p>
  <div class="summary">
    <span class="chip {status_class}">判定: {status}</span>
    <span class="chip error">ERROR {errors}</span>
    <span class="chip warning">WARNING {warnings}</span>
    <span class="chip info">INFO {infos}</span>
    <span class="chip">処理時間 {elapsed:.2f} 秒</span>
  </div>

  <h2>指摘一覧（{total}件）</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>重大度</th>
        <th>ルールID / JIS根拠</th>
        <th>ページ</th>
        <th>指摘内容</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def write(
    report: CheckReport,
    output_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    if output_path is None:
        src = Path(report.drawing_path)
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / (src.stem + "_report.html")
        else:
            output_path = src.with_name(src.stem + "_report.html")

    rows: list[str] = []
    for i, f in enumerate(report.findings, 1):
        severity = f.severity.value
        jis = html.escape(f.jis_reference) if f.jis_reference else "-"
        suggestion_html = (
            f'<div class="suggestion">→ {html.escape(f.suggestion)}</div>'
            if f.suggestion else ""
        )
        rows.append(
            f'      <tr class="{severity}">'
            f'<td>{i}</td>'
            f'<td>{severity.upper()}</td>'
            f'<td><span class="rule-id">{html.escape(f.rule_id)}</span>'
            f'<div class="jis">{jis}</div></td>'
            f'<td>p.{f.page_number}</td>'
            f'<td>{html.escape(f.message)}{suggestion_html}</td>'
            f'</tr>'
        )

    status = "合格" if report.is_pass else "不合格（要修正）"
    status_class = "pass" if report.is_pass else "fail"

    html_text = HTML_TEMPLATE.format(
        filename=html.escape(Path(report.drawing_path).name),
        filepath=html.escape(report.drawing_path),
        status=status,
        status_class=status_class,
        errors=report.errors_count,
        warnings=report.warnings_count,
        infos=report.info_count,
        elapsed=report.processing_time_sec,
        total=len(report.findings),
        rows="\n".join(rows) if rows else
             '      <tr><td colspan="5" style="text-align:center;color:#888;">指摘事項はありません</td></tr>',
    )

    output_path.write_text(html_text, encoding="utf-8")
    return output_path
