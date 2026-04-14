import { useState } from 'react';
import type { Section } from '../types';
import SectionDetail from './SectionDetail';

interface Props {
  recordingId: string;
  sections: Section[];
  onSectionsUpdate: (sections: Section[]) => void;
  onTimeClick: (time: number) => void;
  isVideo: boolean;
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function VideoSections({ recordingId, sections, onSectionsUpdate, onTimeClick, isVideo }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const generateSections = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/sections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recordingId }),
      });
      if (res.ok) {
        const data = await res.json();
        onSectionsUpdate(data);
      }
    } catch (err) {
      console.error('セクション分割エラー:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCommentUpdate = async (sectionId: string, comment: string) => {
    try {
      await fetch(`/api/sections/${sectionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment }),
      });
      onSectionsUpdate(sections.map(s => s.id === sectionId ? { ...s, user_comment: comment } : s));
    } catch {}
  };

  if (sections.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 mb-4">セクション分割がまだ実行されていません</p>
        <button onClick={generateSections} className="btn-primary" disabled={loading}>
          {loading ? '分割中...' : 'セクション分割を実行'}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {sections.map((section) => (
        <div key={section.id} className="card overflow-hidden">
          {/* ヘッダー */}
          <button
            onClick={() => setExpandedId(expandedId === section.id ? null : section.id)}
            className="w-full flex items-center gap-3 p-4 text-left hover:bg-dark-hover transition-colors"
          >
            <span className="text-xs font-mono text-accent-blue min-w-[50px]">
              #{section.section_index + 1}
            </span>

            <button
              onClick={(e) => { e.stopPropagation(); onTimeClick(section.start_time); }}
              className={`text-xs font-mono whitespace-nowrap ${
                isVideo ? 'text-accent-blue hover:underline' : 'text-gray-500'
              }`}
            >
              {formatTime(section.start_time)} - {formatTime(section.end_time)}
            </button>

            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm truncate">{section.title}</h4>
              <p className="text-xs text-gray-500 truncate">{section.summary}</p>
            </div>

            <svg
              className={`w-4 h-4 text-gray-500 transition-transform ${expandedId === section.id ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* 展開コンテンツ */}
          {expandedId === section.id && (
            <SectionDetail
              section={section}
              onTimeClick={onTimeClick}
              onCommentUpdate={handleCommentUpdate}
              isVideo={isVideo}
            />
          )}
        </div>
      ))}
    </div>
  );
}
