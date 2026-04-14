import { useState } from 'react';
import type { Transcription, TranscriptSegment } from '../types';

interface Props {
  transcription: Transcription;
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

const speakerColors = [
  'text-blue-400', 'text-green-400', 'text-purple-400',
  'text-orange-400', 'text-pink-400', 'text-cyan-400',
];

export default function TranscriptView({ transcription, onTimeClick, isVideo }: Props) {
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'segments' | 'fulltext'>('segments');

  const segments: TranscriptSegment[] = transcription.segments || [];
  const speakerMap = new Map<string, number>();

  const getSpeakerColor = (speaker?: string) => {
    if (!speaker) return 'text-gray-400';
    if (!speakerMap.has(speaker)) {
      speakerMap.set(speaker, speakerMap.size);
    }
    return speakerColors[speakerMap.get(speaker)! % speakerColors.length];
  };

  const filteredSegments = searchQuery
    ? segments.filter(s => s.text.toLowerCase().includes(searchQuery.toLowerCase()))
    : segments;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(transcription.full_text);
  };

  return (
    <div className="space-y-4">
      {/* ツールバー */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="テキスト検索..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-3 py-2 bg-dark-surface border border-dark-border rounded-lg text-sm focus:outline-none focus:border-accent-blue"
        />
        <div className="flex bg-dark-surface border border-dark-border rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode('segments')}
            className={`px-3 py-2 text-xs ${viewMode === 'segments' ? 'bg-accent-blue text-white' : 'text-gray-400'}`}
          >
            セグメント
          </button>
          <button
            onClick={() => setViewMode('fulltext')}
            className={`px-3 py-2 text-xs ${viewMode === 'fulltext' ? 'bg-accent-blue text-white' : 'text-gray-400'}`}
          >
            全文
          </button>
        </div>
        <button onClick={copyToClipboard} className="btn-secondary text-xs" title="全文コピー">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </button>
      </div>

      {/* コンテンツ */}
      {viewMode === 'fulltext' ? (
        <div className="card p-4 whitespace-pre-wrap text-sm leading-relaxed">
          {transcription.full_text}
        </div>
      ) : (
        <div className="space-y-1">
          {filteredSegments.map((seg, idx) => (
            <div key={idx} className="flex gap-3 p-2 hover:bg-dark-hover rounded-lg group">
              {/* タイムスタンプ */}
              <button
                onClick={() => onTimeClick(seg.start)}
                className={`text-xs font-mono whitespace-nowrap ${
                  isVideo ? 'text-accent-blue hover:underline cursor-pointer' : 'text-gray-500'
                }`}
              >
                {formatTime(seg.start)}
              </button>

              {/* 話者 */}
              {seg.speaker && (
                <span className={`text-xs font-medium whitespace-nowrap ${getSpeakerColor(seg.speaker)}`}>
                  {seg.speaker}
                </span>
              )}

              {/* テキスト */}
              <p className="text-sm flex-1">{seg.text}</p>
            </div>
          ))}

          {filteredSegments.length === 0 && searchQuery && (
            <p className="text-center text-gray-500 py-8">「{searchQuery}」は見つかりませんでした</p>
          )}
        </div>
      )}
    </div>
  );
}
