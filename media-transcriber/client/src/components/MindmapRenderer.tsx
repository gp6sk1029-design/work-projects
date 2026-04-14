import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import type { MindmapData } from '../types';

interface Props {
  recordingId: string;
  mindmaps: MindmapData[];
  onMindmapsUpdate: (mindmaps: MindmapData[]) => void;
}

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#3b82f6',
    primaryTextColor: '#e5e7eb',
    primaryBorderColor: '#353a50',
    lineColor: '#6b7280',
    secondaryColor: '#232738',
    tertiaryColor: '#1a1d2e',
  },
});

export default function MindmapRenderer({ recordingId, mindmaps, onMindmapsUpdate }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wholeMindmap = mindmaps.find(m => !m.section_id);

  useEffect(() => {
    if (!wholeMindmap || !containerRef.current) return;
    renderMermaid(wholeMindmap.mermaid_code);
  }, [wholeMindmap]);

  async function renderMermaid(code: string) {
    if (!containerRef.current) return;
    try {
      const id = `mermaid-${Date.now()}`;
      const { svg } = await mermaid.render(id, code);
      containerRef.current.innerHTML = svg;
      setError(null);
    } catch (err: any) {
      setError('マインドマップの描画に失敗しました');
      containerRef.current.innerHTML = `<pre class="text-sm text-gray-400 p-4">${code}</pre>`;
    }
  }

  const generateMindmap = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/mindmap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recordingId }),
      });
      if (res.ok) {
        const mindmap = await res.json();
        onMindmapsUpdate([...mindmaps.filter(m => m.section_id), mindmap]);
      }
    } catch (err) {
      setError('マインドマップ生成に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const downloadSvg = () => {
    if (!containerRef.current) return;
    const svg = containerRef.current.querySelector('svg');
    if (!svg) return;
    const blob = new Blob([svg.outerHTML], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mindmap.svg';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-400">論理構造マインドマップ</h3>
        <div className="flex gap-2">
          {!wholeMindmap && (
            <button onClick={generateMindmap} className="btn-primary text-sm" disabled={loading}>
              {loading ? '生成中...' : '生成'}
            </button>
          )}
          {wholeMindmap && (
            <button onClick={downloadSvg} className="btn-secondary text-xs">
              SVGダウンロード
            </button>
          )}
        </div>
      </div>

      <div className="card p-6 min-h-[400px]">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full" />
            <span className="ml-3 text-gray-400">マインドマップ生成中...</span>
          </div>
        ) : (
          <div ref={containerRef} className="flex justify-center overflow-auto" />
        )}

        {error && (
          <p className="text-sm text-accent-red mt-2">{error}</p>
        )}

        {!wholeMindmap && !loading && (
          <p className="text-center text-gray-500 py-12">
            「生成」ボタンをクリックしてマインドマップを作成してください
          </p>
        )}
      </div>
    </div>
  );
}
