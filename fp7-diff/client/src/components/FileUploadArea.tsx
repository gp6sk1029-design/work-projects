import { useState, useRef } from 'react';

interface Props {
  label: string;
  color: string;
  file: File | null;
  onFileChange: (file: File | null) => void;
}

export default function FileUploadArea({ label, color, file, onFileChange }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onFileChange(f);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex-1 cursor-pointer border-2 border-dashed rounded-lg p-6 transition ${
        dragOver ? 'border-accent-400 bg-accent-500/10' : `border-${color} bg-dark-surface hover:bg-dark-hover/30`
      }`}
      style={{ borderColor: file ? '#10b981' : undefined }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.csv"
        className="hidden"
        onChange={(e) => onFileChange(e.target.files?.[0] || null)}
      />
      <div className="text-center">
        <div className={`text-3xl mb-2`}>{file ? '✅' : '📄'}</div>
        <p className="text-sm font-semibold text-gray-300 mb-1">{label}</p>
        {file ? (
          <>
            <p className="text-xs text-green-400 break-all">{file.name}</p>
            <p className="text-xs text-gray-500 mt-1">{(file.size / 1024).toFixed(1)} KB</p>
            <button
              onClick={(e) => { e.stopPropagation(); onFileChange(null); }}
              className="mt-2 text-xs text-red-400 hover:text-red-300"
            >
              削除
            </button>
          </>
        ) : (
          <>
            <p className="text-xs text-gray-400">クリック or ドラッグ&ドロップ</p>
            <p className="text-xs text-gray-500 mt-1">FPWIN GR7 「グローバルデバイス.txt」</p>
          </>
        )}
      </div>
    </div>
  );
}
