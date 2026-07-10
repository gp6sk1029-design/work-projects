import { useState, useMemo } from 'react';
import type { DiffResult, DiffStatus, DeviceCategory, DiffRow } from '../types';

interface Props {
  diff: DiffResult;
}

const STATUS_STYLES: Record<DiffStatus, { bg: string; label: string }> = {
  changed: { bg: 'bg-yellow-900/30 border-l-4 border-l-yellow-500', label: '🟡 変更' },
  added: { bg: 'bg-green-900/30 border-l-4 border-l-green-500', label: '🟢 追加(B)' },
  removed: { bg: 'bg-red-900/30 border-l-4 border-l-red-500', label: '🔴 削除(A)' },
  same: { bg: 'bg-dark-surface border-l-4 border-l-transparent', label: '⚪ 同一' },
};

export default function DiffViewer({ diff }: Props) {
  const [filter, setFilter] = useState<DiffStatus | 'all'>('changed');
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<DeviceCategory | 'all'>('all');
  const [showSame] = useState(false);

  const categories = useMemo(() => {
    const set = new Set<DeviceCategory>();
    diff.rows.forEach((r) => set.add(r.category));
    return Array.from(set).sort();
  }, [diff.rows]);

  const filtered = useMemo(() => {
    return diff.rows.filter((r) => {
      if (filter !== 'all' && r.status !== filter) return false;
      if (filter === 'all' && !showSame && r.status === 'same') return false;
      if (categoryFilter !== 'all' && r.category !== categoryFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        if (
          !r.address.toLowerCase().includes(q) &&
          !r.commentA.toLowerCase().includes(q) &&
          !r.commentB.toLowerCase().includes(q)
        ) return false;
      }
      return true;
    });
  }, [diff.rows, filter, categoryFilter, search, showSame]);

  const exportCsv = () => {
    const rows = filtered.map((r) => [
      r.address,
      r.category,
      r.status,
      r.commentA.replace(/"/g, '""'),
      r.commentB.replace(/"/g, '""'),
    ].map((c) => `"${c}"`).join(','));
    const csv = '﻿' + 'アドレス,カテゴリ,状態,A側コメント,B側コメント\n' + rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fp7-diff_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* フィルタ */}
      <div className="flex flex-wrap gap-3 p-3 bg-dark-surface rounded border border-dark-border">
        <div className="flex gap-1">
          {(['all', 'changed', 'added', 'removed', 'same'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1.5 text-xs rounded transition ${
                filter === s
                  ? 'bg-accent-600 text-white'
                  : 'bg-dark-bg text-gray-400 hover:text-white'
              }`}
            >
              {s === 'all' ? '全て' : STATUS_STYLES[s].label}
            </button>
          ))}
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as DeviceCategory | 'all')}
          className="px-3 py-1.5 text-xs bg-dark-bg border border-dark-border rounded text-gray-300"
        >
          <option value="all">全カテゴリ</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="アドレス/コメント検索..."
          className="px-3 py-1.5 text-xs bg-dark-bg border border-dark-border rounded text-white flex-1 min-w-[200px]"
        />
        <button
          onClick={exportCsv}
          className="px-3 py-1.5 text-xs bg-accent-600 hover:bg-accent-500 text-white rounded"
        >
          📥 CSV出力
        </button>
      </div>

      {/* 件数表示 */}
      <p className="text-xs text-gray-400">
        表示中: {filtered.length} / {diff.rows.length} 件
      </p>

      {/* テーブル */}
      <div className="overflow-x-auto rounded border border-dark-border">
        <table className="w-full text-sm">
          <thead className="bg-dark-surface text-xs text-gray-400 border-b border-dark-border sticky top-0">
            <tr>
              <th className="text-left py-2 px-3 w-24">アドレス</th>
              <th className="text-left py-2 px-3 w-16">分類</th>
              <th className="text-left py-2 px-3 w-28">状態</th>
              <th className="text-left py-2 px-3">A側コメント</th>
              <th className="text-left py-2 px-3">B側コメント</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 1000).map((r, i) => (
              <DiffRowItem key={`${r.address}-${i}`} row={r} />
            ))}
          </tbody>
        </table>
        {filtered.length > 1000 && (
          <p className="text-center text-xs text-gray-500 py-3">
            ... 上位1000件のみ表示中。CSV出力で全件確認できます。
          </p>
        )}
      </div>
    </div>
  );
}

function DiffRowItem({ row }: { row: DiffRow }) {
  const style = STATUS_STYLES[row.status];
  return (
    <tr className={`${style.bg} border-b border-dark-border/30`}>
      <td className="py-1.5 px-3 font-mono text-white">{row.address}</td>
      <td className="py-1.5 px-3 text-gray-400 text-xs">{row.category}</td>
      <td className="py-1.5 px-3 text-xs">{style.label}</td>
      <td className="py-1.5 px-3 text-gray-300">{row.commentA || <span className="text-gray-600">(なし)</span>}</td>
      <td className="py-1.5 px-3 text-gray-300">
        {row.commentB || <span className="text-gray-600">(なし)</span>}
      </td>
    </tr>
  );
}
