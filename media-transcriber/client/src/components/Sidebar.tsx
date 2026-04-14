import { useEffect, useState } from 'react';
import type { HistoryItem } from '../types';

interface Props {
  isOpen: boolean;
  history: HistoryItem[];
  setHistory: (items: HistoryItem[]) => void;
  onSelect: (id: string) => void;
  onClose: () => void;
  onNewUpload: () => void;
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}時間${m}分`;
  return `${m}分`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export default function Sidebar({ isOpen, history, setHistory, onSelect, onClose, onNewUpload }: Props) {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetch('/api/history')
        .then(res => res.json())
        .then(data => setHistory(data))
        .catch(() => {});
    }
    // サイドバーを閉じたら確認ダイアログもリセット
    if (!isOpen) setDeleteConfirm(null);
  }, [isOpen]);

  const handleDelete = async (id: string) => {
    setDeleting(true);
    try {
      const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
      if (res.ok) {
        // 履歴リストから削除
        setHistory(history.filter(h => h.id !== id));
        setDeleteConfirm(null);
      }
    } catch (err) {
      console.error('削除エラー:', err);
    } finally {
      setDeleting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* オーバーレイ */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* サイドバー */}
      <div className="fixed left-0 top-0 bottom-0 w-80 bg-dark-surface border-r border-dark-border z-50 flex flex-col">
        {/* ヘッダー */}
        <div className="flex items-center justify-between p-4 border-b border-dark-border">
          <h2 className="font-bold">録音履歴</h2>
          <button onClick={onClose} className="p-1 hover:bg-dark-hover rounded">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 新規アップロードボタン */}
        <div className="p-3">
          <button onClick={onNewUpload} className="btn-primary w-full text-sm">
            + 新規アップロード
          </button>
        </div>

        {/* 注釈 */}
        <div className="px-3 pb-2">
          <p className="text-xs text-gray-600">
            削除するとアップロードファイル・文字起こし・要約など全データが完全に削除されます
          </p>
        </div>

        {/* 履歴リスト */}
        <div className="flex-1 overflow-auto">
          {history.length === 0 ? (
            <p className="text-center text-gray-500 py-8 text-sm">履歴がありません</p>
          ) : (
            <div className="divide-y divide-dark-border">
              {history.map((item) => (
                <div key={item.id} className="relative group">
                  {/* 削除確認ダイアログ */}
                  {deleteConfirm === item.id ? (
                    <div className="p-3 bg-red-500/10 border-l-2 border-red-500">
                      <p className="text-xs text-red-400 mb-2">
                        この録音と関連する全データ（ファイル・文字起こし・要約・Q&A）を削除しますか？
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDelete(item.id)}
                          disabled={deleting}
                          className="px-3 py-1 text-xs bg-red-500 hover:bg-red-600 text-white rounded transition-colors disabled:opacity-50"
                        >
                          {deleting ? '削除中...' : '削除する'}
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(null)}
                          className="px-3 py-1 text-xs bg-dark-card hover:bg-dark-hover text-gray-300 rounded border border-dark-border transition-colors"
                        >
                          キャンセル
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center">
                      {/* 録音情報（クリックで結果表示） */}
                      <button
                        onClick={() => onSelect(item.id)}
                        className="flex-1 p-3 text-left hover:bg-dark-hover transition-colors"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs">
                            {item.is_video ? '🎬' : '🎤'}
                          </span>
                          <span className="text-sm font-medium truncate flex-1">
                            {item.file_name}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span>{formatDate(item.created_at)}</span>
                          <span>{formatDuration(item.duration_seconds)}</span>
                          {item.has_transcription && (
                            <span className="text-green-400">文字起こし済</span>
                          )}
                        </div>
                      </button>

                      {/* 削除ボタン */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteConfirm(item.id);
                        }}
                        className="p-2 mr-2 text-gray-500 hover:text-red-400 transition-colors"
                        title="この録音を削除"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* フッター注釈 */}
        <div className="p-3 border-t border-dark-border">
          <p className="text-xs text-gray-600 text-center">
            保存先: server/uploads/
          </p>
        </div>
      </div>
    </>
  );
}
