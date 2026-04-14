import { useState } from 'react';

interface Props {
  recordingId: string;
  fileName: string;
  onClose: () => void;
}

const exportFormats = [
  {
    key: 'xlsx',
    label: 'Excel (.xlsx)',
    description: '文字起こし・要約・セクション・Q&Aをシート別に出力',
    icon: '📊',
  },
  {
    key: 'docx',
    label: 'Word (.docx)',
    description: '議事録形式のドキュメント。印刷・共有に最適',
    icon: '📄',
  },
  {
    key: 'json',
    label: '再読み込み用 (.mt.json.gz)',
    description: 'このツールで再度開けるファイル。容量最小・圧縮済み',
    icon: '💾',
  },
];

export default function ExportDialog({ recordingId, fileName, onClose }: Props) {
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleExport = async (format: string) => {
    setDownloading(format);
    try {
      const res = await fetch(`/api/export/${format}/${recordingId}`);
      if (!res.ok) throw new Error('エクスポートに失敗しました');

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;

      const baseName = fileName.replace(/\.\w+$/, '');
      const ext = format === 'json' ? '.mt.json.gz' : `.${format}`;
      a.download = `${baseName}${ext}`;

      document.body.appendChild(a);
      a.click();

      // クリーンアップ
      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (err: any) {
      console.error('エクスポートエラー:', err);
      alert('エクスポートに失敗しました: ' + (err.message || ''));
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="bg-dark-card border border-dark-border rounded-xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-lg font-bold">保存形式を選択</h2>
          <button onClick={onClose} className="p-1 hover:bg-dark-hover rounded">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-3">
          {exportFormats.map((fmt) => (
            <button
              key={fmt.key}
              onClick={() => handleExport(fmt.key)}
              disabled={downloading !== null}
              className="w-full flex items-start gap-3 p-4 bg-dark-surface border border-dark-border rounded-lg hover:border-accent-blue/50 transition-colors text-left disabled:opacity-50"
            >
              <span className="text-2xl">{fmt.icon}</span>
              <div className="flex-1">
                <p className="font-medium text-sm">{fmt.label}</p>
                <p className="text-xs text-gray-500 mt-1">{fmt.description}</p>
              </div>
              {downloading === fmt.key && (
                <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
              )}
            </button>
          ))}
        </div>

        <p className="text-xs text-gray-600 mt-4 text-center">
          Excel・Wordは文章のみ（動画なし）で出力されます
        </p>
      </div>
    </div>
  );
}
