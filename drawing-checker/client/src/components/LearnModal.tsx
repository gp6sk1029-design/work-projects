import { useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import type { LearnResponse, SampleItem, SamplesResponse } from '../types';

interface Props {
  onClose: () => void;
}

type Tab = 'existing' | 'add';

export default function LearnModal({ onClose }: Props) {
  const [tab, setTab] = useState<Tab>('existing');
  const [samples, setSamples] = useState<SampleItem[]>([]);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [newFiles, setNewFiles] = useState<File[]>([]);
  const [noAi, setNoAi] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<LearnResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewName, setPreviewName] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples();
  }, []);

  async function fetchSamples() {
    setLoadingSamples(true);
    try {
      const r = await fetch('/api/samples');
      if (r.ok) {
        const data = (await r.json()) as SamplesResponse;
        setSamples(data.items);
      }
    } finally {
      setLoadingSamples(false);
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    multiple: true,
    disabled: running,
    onDrop: (accepted) => {
      setNewFiles((prev) => [...prev, ...accepted]);
    },
  });

  async function handleDelete(item: SampleItem) {
    if (!confirm(`「${item.filename}」を削除しますか？\n※削除後は再学習を実行してください。`)) return;
    try {
      const r = await fetch(
        `/api/samples/${encodeURIComponent(item.batchId)}/${encodeURIComponent(item.filename)}`,
        { method: 'DELETE' },
      );
      if (!r.ok) {
        const err = await r.json().catch(() => ({ error: '削除に失敗' }));
        alert(err.error);
        return;
      }
      await fetchSamples();
    } catch (e: any) {
      alert(e.message);
    }
  }

  async function handleDeleteAll() {
    if (!confirm('全サンプルと学習済みルールをリセットします。本当によろしいですか？')) return;
    try {
      const r = await fetch('/api/samples', { method: 'DELETE' });
      if (!r.ok) throw new Error('リセットに失敗');
      await fetchSamples();
      alert('全サンプルをリセットしました。');
    } catch (e: any) {
      alert(e.message);
    }
  }

  async function handleAddAndLearn() {
    if (newFiles.length === 0) return;
    setRunning(true);
    setError(null);
    try {
      // 新規ファイルをアップロード（サンプルとして保存のみ）
      const fd = new FormData();
      for (const f of newFiles) fd.append('files', f);
      if (noAi) fd.append('noAi', 'true');

      const r = await fetch('/api/learn', { method: 'POST', body: fd });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ error: 'サーバーエラー' }));
        throw new Error(err.error || `HTTP ${r.status}`);
      }
      const data = (await r.json()) as LearnResponse;
      setResult(data);
      setNewFiles([]);
      await fetchSamples();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  async function handleRelearn() {
    if (samples.length === 0) {
      setError('サンプルがありません。先に追加アップロードしてください。');
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const r = await fetch('/api/samples/relearn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ noAi }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ error: 'サーバーエラー' }));
        throw new Error(err.error || `HTTP ${r.status}`);
      }
      const data = (await r.json()) as LearnResponse;
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  function fmtSize(bytes: number): string {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  }

  function fmtDate(iso: string): string {
    try {
      const d = new Date(iso);
      return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    } catch {
      return iso;
    }
  }

  const totalBytes = samples.reduce((s, i) => s + i.size_bytes, 0);

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-dark-surface border border-dark-border rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ヘッダー */}
        <div className="px-6 py-4 border-b border-dark-border flex items-center justify-between shrink-0">
          <div>
            <h2 className="text-lg font-bold">🎓 サンプル図面の管理・学習</h2>
            <p className="text-xs text-slate-400 mt-1">
              現在 {samples.length} 枚（{fmtSize(totalBytes)}）を学習対象にしています
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl leading-none">×</button>
        </div>

        {/* タブ */}
        <div className="flex border-b border-dark-border shrink-0">
          <button
            onClick={() => setTab('existing')}
            className={`px-6 py-2.5 text-sm font-medium border-b-2 transition ${
              tab === 'existing' ? 'border-accent text-accent' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            📋 既存サンプル ({samples.length})
          </button>
          <button
            onClick={() => setTab('add')}
            className={`px-6 py-2.5 text-sm font-medium border-b-2 transition ${
              tab === 'add' ? 'border-accent text-accent' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            ➕ 追加アップロード
          </button>
        </div>

        {/* 本体 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {tab === 'existing' && (
            <>
              {loadingSamples ? (
                <div className="text-center text-slate-400 py-8">読み込み中...</div>
              ) : samples.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <div className="text-4xl mb-2">📂</div>
                  <div>まだサンプルがありません</div>
                  <div className="text-xs mt-2">「➕ 追加アップロード」タブから合格図面を追加してください</div>
                </div>
              ) : (
                <>
                  <div className="bg-dark-bg/60 rounded-lg overflow-hidden border border-dark-border">
                    <table className="w-full text-sm">
                      <thead className="bg-dark-bg text-xs text-slate-400">
                        <tr>
                          <th className="text-left px-3 py-2">#</th>
                          <th className="text-left px-3 py-2">ファイル名</th>
                          <th className="text-right px-3 py-2">サイズ</th>
                          <th className="text-right px-3 py-2">追加日時</th>
                          <th className="px-3 py-2 w-24"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dark-border">
                        {samples.map((s, i) => (
                          <tr key={`${s.batchId}/${s.filename}`} className="hover:bg-dark-hover/40">
                            <td className="px-3 py-2 text-slate-500">{i + 1}</td>
                            <td className="px-3 py-2">
                              <div className="font-medium truncate max-w-xs">{s.filename}</div>
                            </td>
                            <td className="px-3 py-2 text-right text-slate-400">{fmtSize(s.size_bytes)}</td>
                            <td className="px-3 py-2 text-right text-slate-400">{fmtDate(s.uploaded_at)}</td>
                            <td className="px-3 py-2 text-right whitespace-nowrap">
                              <button
                                onClick={() => { setPreviewUrl(s.url); setPreviewName(s.filename); }}
                                className="px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-xs mr-1"
                                title="プレビュー"
                              >
                                👁
                              </button>
                              <button
                                onClick={() => handleDelete(s)}
                                className="px-2 py-1 rounded bg-red-600/70 hover:bg-red-500 text-xs"
                                title="削除"
                                disabled={running}
                              >
                                🗑
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-2">
                    <button
                      onClick={handleDeleteAll}
                      className="text-xs text-red-400 hover:text-red-300 underline"
                      disabled={running}
                    >
                      全サンプルをリセット
                    </button>
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 text-xs cursor-pointer">
                        <input
                          type="checkbox"
                          checked={noAi}
                          onChange={(e) => setNoAi(e.target.checked)}
                          className="w-3.5 h-3.5 rounded accent-accent"
                          disabled={running}
                        />
                        <span className="text-slate-300">AIを使わない</span>
                      </label>
                      <button
                        onClick={handleRelearn}
                        disabled={running || samples.length === 0}
                        className={`px-4 py-2 rounded-lg text-sm font-medium ${
                          running || samples.length === 0
                            ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                            : 'bg-accent text-slate-900 hover:bg-cyan-300'
                        }`}
                      >
                        {running ? '学習中...' : '🔄 残りのサンプルで再学習'}
                      </button>
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {tab === 'add' && (
            <>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer ${
                  isDragActive ? 'border-accent bg-accent/5' : 'border-dark-border hover:border-slate-500'
                } ${running ? 'opacity-60 cursor-not-allowed' : ''}`}
              >
                <input {...getInputProps()} />
                <div className="text-3xl mb-2">📂</div>
                <div className="text-sm">
                  {isDragActive ? 'ここにドロップ！' : '合格図面を複数ドロップ（何枚でもOK・多いほど精度UP）'}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  PDF / DXF / DWG / PNG / JPG ・ 最大200枚・1ファイル100MBまで
                </div>
              </div>

              {newFiles.length > 0 && (
                <div className="bg-dark-bg rounded-lg p-3 max-h-40 overflow-y-auto">
                  <div className="text-xs text-slate-400 mb-1">{newFiles.length}件選択中</div>
                  <ul className="text-xs space-y-0.5">
                    {newFiles.map((f, i) => (
                      <li key={i} className="flex justify-between items-center">
                        <span className="truncate">{f.name}</span>
                        <button
                          onClick={() => setNewFiles((fs) => fs.filter((_, j) => j !== i))}
                          className="text-red-400 hover:text-red-300 ml-2"
                          disabled={running}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={noAi}
                  onChange={(e) => setNoAi(e.target.checked)}
                  className="w-4 h-4 rounded accent-accent"
                  disabled={running}
                />
                <span>AI（Gemini）を使わず、統計のみで学習する（無料・精度やや低）</span>
              </label>

              <div className="flex justify-end gap-2">
                <button
                  onClick={handleAddAndLearn}
                  disabled={newFiles.length === 0 || running}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${
                    newFiles.length === 0 || running
                      ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                      : 'bg-accent text-slate-900 hover:bg-cyan-300'
                  }`}
                >
                  {running ? '学習中...' : '➕ 追加して学習'}
                </button>
              </div>
            </>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              ❌ {error}
            </div>
          )}

          {result && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/40">
              <div className="flex items-center gap-3">
                <div className="text-2xl">✅</div>
                <div className="text-sm">
                  学習完了：<span className="font-bold">{result.filesLearned}件</span>
                  のサンプルから <span className="font-bold">{result.rulesCount}件</span>
                  のルールを生成
                </div>
              </div>
            </div>
          )}
        </div>

        {/* フッター */}
        <div className="px-6 py-3 border-t border-dark-border text-xs text-slate-400 shrink-0">
          💡 悪いサンプルを削除したら「🔄 残りのサンプルで再学習」で更新してください
        </div>
      </div>

      {/* プレビューウィンドウ */}
      {previewUrl && (
        <div
          className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center p-4"
          onClick={() => setPreviewUrl(null)}
        >
          <div className="relative max-w-5xl max-h-[90vh] w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm text-slate-300">{previewName}</div>
              <button onClick={() => setPreviewUrl(null)} className="text-white text-2xl leading-none">×</button>
            </div>
            {/\.(pdf)$/i.test(previewName || '') ? (
              <iframe src={previewUrl} className="w-full h-[80vh] rounded bg-white" />
            ) : /\.(png|jpe?g|bmp|tiff?|gif)$/i.test(previewName || '') ? (
              <img src={previewUrl} className="max-h-[80vh] max-w-full mx-auto rounded" />
            ) : (
              <div className="bg-dark-surface rounded p-8 text-center text-slate-400">
                <div className="text-4xl mb-2">📄</div>
                <div>このファイル形式はブラウザでプレビューできません</div>
                <a href={previewUrl} download className="text-accent underline text-sm mt-3 inline-block">
                  ダウンロード
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
