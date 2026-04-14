import { useState } from 'react';
import type { SummaryData, SummaryType } from '../types';

interface Props {
  recordingId: string;
  summaries: SummaryData[];
  onSummariesUpdate: (summaries: SummaryData[]) => void;
}

const summaryTabs: { key: SummaryType; label: string; description: string }[] = [
  { key: 'brief', label: '簡潔', description: '3〜5行の要点' },
  { key: 'detailed', label: '詳細', description: '構造化された詳細要約' },
  { key: 'minutes', label: '議事録', description: '会議議事録形式' },
  { key: 'action_items', label: 'アクション', description: 'タスク・ToDoリスト' },
];

export default function SummaryPanel({ recordingId, summaries, onSummariesUpdate }: Props) {
  const [activeType, setActiveType] = useState<SummaryType>('brief');
  const [loading, setLoading] = useState(false);

  const currentSummary = summaries.find(s => s.summary_type === activeType);

  const generateSummary = async (type: SummaryType) => {
    if (summaries.find(s => s.summary_type === type)) return;

    setLoading(true);
    try {
      const res = await fetch('/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recordingId, type }),
      });
      if (res.ok) {
        const summary = await res.json();
        onSummariesUpdate([...summaries, summary]);
      }
    } catch (err) {
      console.error('要約生成エラー:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTabClick = (type: SummaryType) => {
    setActiveType(type);
    if (!summaries.find(s => s.summary_type === type)) {
      generateSummary(type);
    }
  };

  const copyToClipboard = () => {
    if (currentSummary) {
      navigator.clipboard.writeText(currentSummary.content);
    }
  };

  return (
    <div className="space-y-4">
      {/* タブ */}
      <div className="flex gap-2">
        {summaryTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => handleTabClick(tab.key)}
            className={`px-3 py-2 rounded-lg text-sm transition-colors ${
              activeType === tab.key
                ? 'bg-accent-blue text-white'
                : 'bg-dark-surface border border-dark-border text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* コンテンツ */}
      <div className="card p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full" />
            <span className="ml-3 text-gray-400">要約を生成中...</span>
          </div>
        ) : currentSummary ? (
          <div>
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-sm font-medium text-gray-400">
                {summaryTabs.find(t => t.key === activeType)?.description}
              </h3>
              <button onClick={copyToClipboard} className="btn-secondary text-xs">
                コピー
              </button>
            </div>
            <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap leading-relaxed">
              {currentSummary.content}
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <p>タブをクリックして要約を生成してください</p>
          </div>
        )}
      </div>
    </div>
  );
}
