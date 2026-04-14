import { useState, useEffect, useRef } from 'react';
import mermaid from 'mermaid';
import type { Section } from '../types';

interface Props {
  section: Section;
  onTimeClick: (time: number) => void;
  onCommentUpdate: (sectionId: string, comment: string) => void;
  isVideo: boolean;
}

export default function SectionDetail({ section, onTimeClick, onCommentUpdate, isVideo }: Props) {
  const [activeTab, setActiveTab] = useState<'text' | 'summary' | 'mindmap' | 'comment'>('text');
  const [comment, setComment] = useState(section.user_comment || '');
  const mindmapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeTab === 'mindmap' && section.mindmap_mermaid && mindmapRef.current) {
      const id = `section-mm-${section.id}-${Date.now()}`;
      mermaid.render(id, section.mindmap_mermaid).then(({ svg }) => {
        if (mindmapRef.current) mindmapRef.current.innerHTML = svg;
      }).catch(() => {
        if (mindmapRef.current) {
          mindmapRef.current.innerHTML = `<pre class="text-xs text-gray-400">${section.mindmap_mermaid}</pre>`;
        }
      });
    }
  }, [activeTab, section.mindmap_mermaid]);

  const handleSaveComment = () => {
    onCommentUpdate(section.id, comment);
  };

  const tabs = [
    { key: 'text', label: '文字起こし' },
    { key: 'summary', label: '要約' },
    { key: 'mindmap', label: 'マップ' },
    { key: 'comment', label: 'コメント' },
  ] as const;

  return (
    <div className="border-t border-dark-border">
      {/* タブ */}
      <div className="flex border-b border-dark-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-xs font-medium ${
              activeTab === tab.key ? 'text-accent-blue border-b border-accent-blue' : 'text-gray-500'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* コンテンツ */}
      <div className="p-4 max-h-64 overflow-auto">
        {activeTab === 'text' && (
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{section.transcript_text || 'テキストなし'}</p>
        )}

        {activeTab === 'summary' && (
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{section.summary || '要約なし'}</p>
        )}

        {activeTab === 'mindmap' && (
          <div ref={mindmapRef} className="flex justify-center">
            {!section.mindmap_mermaid && <p className="text-sm text-gray-500">マインドマップなし</p>}
          </div>
        )}

        {activeTab === 'comment' && (
          <div className="space-y-2">
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="このセクションにコメントを追加..."
              className="w-full h-24 px-3 py-2 bg-dark-surface border border-dark-border rounded-lg text-sm resize-none focus:outline-none focus:border-accent-blue"
            />
            <button onClick={handleSaveComment} className="btn-primary text-xs">
              保存
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
