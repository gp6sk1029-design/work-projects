import { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface Props {
  diagram?: string;
}

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#a855f7',
    primaryTextColor: '#f3f4f6',
    primaryBorderColor: '#7c3aed',
    lineColor: '#6b7280',
    secondaryColor: '#1a1d27',
    tertiaryColor: '#252836',
  },
});

export default function ScreenTransitionTab({ diagram }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!diagram || !containerRef.current) return;

    const render = async () => {
      try {
        containerRef.current!.innerHTML = '';
        const { svg } = await mermaid.render('screen-transition', diagram);
        containerRef.current!.innerHTML = svg;
      } catch (err) {
        console.error('Mermaid レンダリングエラー:', err);
        containerRef.current!.innerHTML = `<pre class="text-red-400 text-sm">${diagram}</pre>`;
      }
    };
    render();
  }, [diagram]);

  if (!diagram) {
    return (
      <div className="text-center text-gray-500 py-12">
        <p className="text-lg mb-2">画面遷移図がありません</p>
        <p className="text-sm">HMI画面定義を含む .smc2 を分析すると生成されます</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-gray-300">HMI 画面遷移図</h2>
      <div
        ref={containerRef}
        className="bg-dark-surface rounded-lg p-6 flex items-center justify-center min-h-[400px] overflow-auto"
      />
      <div className="bg-dark-surface rounded p-3">
        <h3 className="text-xs font-semibold text-gray-400 mb-2">Mermaid ソース</h3>
        <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{diagram}</pre>
      </div>
    </div>
  );
}
