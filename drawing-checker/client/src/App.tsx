import { useEffect, useState } from 'react';
import type { CheckResponse, InfoResponse } from './types';
import UploadPanel from './components/UploadPanel';
import ResultPanel from './components/ResultPanel';
import PdfPreview from './components/PdfPreview';
import LearnModal from './components/LearnModal';

type Tab = 'check' | 'learn';

export default function App() {
  const [info, setInfo] = useState<InfoResponse | null>(null);
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [useAi, setUseAi] = useState(false);
  const [showLearn, setShowLearn] = useState(false);
  const [selectedFindingIndex, setSelectedFindingIndex] = useState<number | null>(null);

  useEffect(() => {
    fetchInfo();
  }, []);

  async function fetchInfo() {
    try {
      const r = await fetch('/api/info');
      if (r.ok) setInfo(await r.json());
    } catch (e) {
      // no-op
    }
  }

  async function handleCheck(file: File) {
    setChecking(true);
    setError(null);
    setResult(null);
    setSelectedFindingIndex(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('ai', useAi ? 'true' : 'false');

      const r = await fetch('/api/check', { method: 'POST', body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ error: 'サーバーエラー' }));
        throw new Error(err.error || `HTTP ${r.status}`);
      }
      const data = (await r.json()) as CheckResponse;
      setResult(data);
    } catch (e: any) {
      setError(e.message || '検図に失敗しました');
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="min-h-screen">
      {/* ヘッダー */}
      <header className="border-b border-dark-border bg-dark-surface/60 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent to-blue-600 flex items-center justify-center text-xl">
              📐
            </div>
            <div>
              <h1 className="text-xl font-bold">検図ツール</h1>
              <p className="text-xs text-slate-400">SolidWorks 2D図面 自動検図（JIS + サンプル学習）</p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-sm">
            {info && (
              <div className="text-slate-400">
                ルール:{' '}
                <span className="text-slate-200 font-medium">JIS {info.jisRulesCount}件</span>
                <span className="mx-1">+</span>
                <span className={info.hasLearnedRules ? 'text-accent font-medium' : 'text-slate-500'}>
                  学習 {info.learnedRulesCount}件
                </span>
              </div>
            )}
            <button
              onClick={() => setShowLearn(true)}
              className="px-3 py-1.5 rounded-md bg-dark-surface border border-dark-border hover:bg-dark-hover text-sm"
            >
              🎓 サンプル学習
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {/* 入力エリア */}
        {!result && (
          <UploadPanel
            onCheck={handleCheck}
            checking={checking}
            useAi={useAi}
            setUseAi={setUseAi}
            error={error}
          />
        )}

        {/* 結果エリア */}
        {result && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-3">
              <PdfPreview
                pdfUrl={result.pdfUrl}
                originalUrl={result.originalUrl}
                originalName={result.originalName}
                findings={result.result.findings}
                selectedIndex={selectedFindingIndex}
              />
            </div>
            <div className="lg:col-span-2">
              <ResultPanel
                response={result}
                onReset={() => {
                  setResult(null);
                  setError(null);
                  setSelectedFindingIndex(null);
                  fetchInfo();
                }}
                selectedIndex={selectedFindingIndex}
                onSelectFinding={setSelectedFindingIndex}
              />
            </div>
          </div>
        )}
      </main>

      {showLearn && (
        <LearnModal
          onClose={() => {
            setShowLearn(false);
            fetchInfo();
          }}
        />
      )}
    </div>
  );
}
