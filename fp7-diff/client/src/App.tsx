import { useState } from 'react';
import type { CompareResponse } from './types';
import FileUploadArea from './components/FileUploadArea';
import DiffSummary from './components/DiffSummary';
import DiffViewer from './components/DiffViewer';
import AiAnalysisPanel from './components/AiAnalysisPanel';
import PdfDiffViewer from './components/PdfDiffViewer';

type TabId = 'summary' | 'table' | 'ai' | 'pdf';
type ModeId = 'variable' | 'pdf';

export default function App() {
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [useAi, setUseAi] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('summary');
  const [mode, setMode] = useState<ModeId>('variable');

  const handleCompare = async () => {
    if (!fileA || !fileB) {
      setError('プロジェクトAとBの両方のファイルを指定してください');
      return;
    }
    setError(null);
    setIsLoading(true);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append('fileA', fileA);
      fd.append('fileB', fileB);
      fd.append('useAi', String(useAi));
      const res = await fetch('/api/compare', { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json();
        setError(err.error || '比較に失敗しました');
        return;
      }
      const data = await res.json();
      setResult(data);
      setActiveTab('summary');
    } catch (err) {
      setError(`通信エラー: ${String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* ヘッダ */}
      <header className="p-4 bg-dark-surface border-b border-dark-border">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">FP7 Diff</h1>
            <p className="text-xs text-gray-400">Panasonic FP7 (FPWIN GR7) プログラム比較ツール</p>
          </div>
          <div className="text-xs text-gray-500">© 2026 一宮電機 生産技術部</div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full p-4 space-y-4">
        {/* モード切替 */}
        <div className="flex border-b border-dark-border">
          <button
            onClick={() => setMode('variable')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              mode === 'variable' ? 'text-accent-400 border-accent-400' : 'text-gray-400 border-transparent hover:text-gray-200'
            }`}
          >
            📋 変数・コメント比較
          </button>
          <button
            onClick={() => setMode('pdf')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              mode === 'pdf' ? 'text-accent-400 border-accent-400' : 'text-gray-400 border-transparent hover:text-gray-200'
            }`}
          >
            📄 PDFラダー図 視覚比較
          </button>
        </div>

        {/*
          重要: 両モードを常時マウントし、display 切替で状態（アップロード済みファイル・
          比較結果・選択中ページ等）を保持する。三項演算子で出し分けるとアンマウントで
          state が破棄されるため避ける。
        */}
        <div style={{ display: mode === 'pdf' ? 'block' : 'none' }}>
          <PdfDiffViewer />
        </div>

        <div style={{ display: mode === 'variable' ? 'block' : 'none' }} className="space-y-4">
        {/* アップロードエリア */}
        <section className="bg-dark-surface rounded-lg border border-dark-border p-4">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">
            📤 比較する2つのプロジェクトをアップロード
          </h2>
          <p className="text-xs text-gray-500 mb-3">
            FPWIN GR7から「グローバルデバイス」をテキスト形式でエクスポートしたファイル（.txt）をドロップしてください。
          </p>
          <div className="flex flex-col md:flex-row gap-4">
            <FileUploadArea
              label="プロジェクト A"
              color="blue-500"
              file={fileA}
              onFileChange={setFileA}
            />
            <div className="flex items-center justify-center text-2xl text-accent-400 px-2">⇄</div>
            <FileUploadArea
              label="プロジェクト B"
              color="orange-500"
              file={fileB}
              onFileChange={setFileB}
            />
          </div>
          <div className="mt-4 flex items-center justify-between flex-wrap gap-2">
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={useAi}
                onChange={(e) => setUseAi(e.target.checked)}
                className="w-4 h-4"
              />
              🤖 AI解説を生成する（Gemini 2.5 Flash）
            </label>
            <button
              onClick={handleCompare}
              disabled={!fileA || !fileB || isLoading}
              className="px-6 py-2 bg-accent-600 hover:bg-accent-500 disabled:bg-accent-600/30 disabled:text-gray-500 text-white font-semibold rounded transition"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  比較中...
                </span>
              ) : (
                '比較実行'
              )}
            </button>
          </div>
        </section>

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded text-red-300 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* 結果 */}
        {result && (
          <>
            <div className="flex border-b border-dark-border">
              {([
                ['summary', '📊 サマリ'],
                ['table', '📋 差分テーブル'],
                ['ai', '🤖 AI解説'],
              ] as [TabId, string][]).map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeTab === id
                      ? 'text-accent-400 border-accent-400'
                      : 'text-gray-400 border-transparent hover:text-gray-200'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <section className="bg-dark-surface/40 rounded-lg p-4">
              {activeTab === 'summary' && <DiffSummary diff={result.diff} />}
              {activeTab === 'table' && <DiffViewer diff={result.diff} />}
              {activeTab === 'ai' && (
                result.aiSummary ? (
                  <AiAnalysisPanel ai={result.aiSummary} />
                ) : (
                  <p className="text-gray-400 text-sm p-4">AI解説は無効でした。比較時に「AI解説を生成する」をオンにしてください。</p>
                )
              )}
            </section>
          </>
        )}

        {!result && !isLoading && (
          <div className="text-center text-gray-500 py-12">
            <p className="text-sm">
              2つのファイルをアップロードして「比較実行」を押してください。
            </p>
          </div>
        )}
        </div>
      </main>
    </div>
  );
}
