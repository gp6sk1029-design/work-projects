import { useState } from 'react';
import type { AnalysisResult } from '../types';

// CSVエクスポート
export function exportIssuesToCsv(result: AnalysisResult): void {
  const headers = ['ID', 'Severity', 'Category', 'Domain', 'Location', 'Variable', 'Description', 'Suggestion', 'Related Variables', 'Related Screens', 'Reference'];

  const rows = result.issues.map((issue) => [
    issue.id,
    issue.severity,
    issue.category,
    issue.domain,
    issue.location,
    issue.variable || '',
    `"${issue.description.replace(/"/g, '""')}"`,
    `"${issue.suggestion.replace(/"/g, '""')}"`,
    (issue.relatedVariables || []).join('; '),
    (issue.relatedScreens || []).join('; '),
    issue.reference || '',
  ]);

  const bom = '\uFEFF';
  const csv = bom + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `plc-analysis-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// クリップボードコピー
export function copyToClipboard(text: string): void {
  navigator.clipboard.writeText(text);
}

// 分析履歴フック
export function useAnalysisHistory() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/history');
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error('履歴取得エラー:', err);
    } finally {
      setLoading(false);
    }
  };

  return { history, loading, fetchHistory };
}
