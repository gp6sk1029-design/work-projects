import { useState, useRef } from 'react';

interface Props {
  onSubmit: (images: string[]) => void;
  onClose: () => void;
  isDiagnosing: boolean;
}

export default function DiagnosisModal({ onSubmit, onClose, isDiagnosing }: Props) {
  const [images, setImages] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((file) => {
      if (!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = () => {
        setImages((prev) => [...prev, reader.result as string]);
      };
      reader.readAsDataURL(file);
    });
  };

  const removeImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-8" onClick={onClose}>
      <div
        className="bg-dark-surface rounded-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="text-purple-400">🔍</span> 総合診断
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl" disabled={isDiagnosing}>&times;</button>
        </div>

        <p className="text-sm text-gray-400 mb-4">
          エラー画面・アラーム画面・操作パネルのスクリーンショットを添付してください。
          アップロード済みのプロジェクトデータと合わせてAIが総合診断します。
        </p>

        {/* ドロップゾーン */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
            isDragging ? 'border-purple-400 bg-purple-500/10' : 'border-dark-border hover:border-purple-400/50'
          } ${isDiagnosing ? 'opacity-50 pointer-events-none' : ''}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
        >
          <svg className="w-10 h-10 mx-auto mb-3 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-sm text-gray-300">クリックまたはドラッグ&ドロップで画像を追加</p>
          <p className="text-xs text-gray-500 mt-1">PNG / JPEG / WebP（複数可）</p>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />

        {/* プレビュー一覧 */}
        {images.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-gray-400 mb-2">添付画像（{images.length}枚）</p>
            <div className="grid grid-cols-4 gap-2">
              {images.map((img, i) => (
                <div key={i} className="relative group">
                  <img src={img} alt={`スクリーンショット ${i + 1}`} className="w-full h-24 object-cover rounded border border-dark-border" />
                  <div className="absolute top-0 left-0 bg-purple-600 text-white text-[10px] font-bold px-1.5 rounded-br">
                    {i + 1}
                  </div>
                  {!isDiagnosing && (
                    <button
                      onClick={() => removeImage(i)}
                      className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-600 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                    >
                      x
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* フッター */}
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition"
            disabled={isDiagnosing}
          >
            キャンセル
          </button>
          <button
            onClick={() => onSubmit(images)}
            disabled={images.length === 0 || isDiagnosing}
            className={`px-5 py-2 rounded-lg text-sm font-bold transition flex items-center gap-2 ${
              images.length === 0 || isDiagnosing
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-purple-600 hover:bg-purple-500 text-white'
            }`}
          >
            {isDiagnosing ? (
              <>
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                診断中...
              </>
            ) : (
              <>診断開始</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
