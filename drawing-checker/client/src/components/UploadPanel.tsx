import { useState } from 'react';
import { useDropzone } from 'react-dropzone';

interface Props {
  onCheck: (file: File) => void;
  checking: boolean;
  useAi: boolean;
  setUseAi: (v: boolean) => void;
  error: string | null;
}

export default function UploadPanel({ onCheck, checking, useAi, setUseAi, error }: Props) {
  const [file, setFile] = useState<File | null>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/octet-stream': ['.dxf', '.dwg', '.slddrw'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/tiff': ['.tif', '.tiff'],
      'image/bmp': ['.bmp'],
    },
    multiple: false,
    disabled: checking,
    onDrop: (accepted) => {
      if (accepted.length > 0) setFile(accepted[0]);
    },
  });

  return (
    <div className="max-w-2xl mx-auto mt-8">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-2xl p-16 text-center cursor-pointer transition-all
          ${isDragActive
            ? 'border-accent bg-accent/5'
            : 'border-dark-border hover:border-slate-500 bg-dark-surface/30'}
          ${checking ? 'opacity-60 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        <div className="text-6xl mb-4">📐</div>
        {file ? (
          <>
            <div className="text-lg font-medium mb-1">{file.name}</div>
            <div className="text-sm text-slate-400">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </div>
            <div className="text-xs text-slate-500 mt-3">
              別のファイルに変更するには再度ドロップまたはクリック
            </div>
          </>
        ) : (
          <>
            <div className="text-lg mb-2">
              {isDragActive ? 'ここにドロップ！' : '図面ファイルをドロップ または クリックして選択'}
            </div>
            <div className="text-sm text-slate-400">
              対応: PDF / DXF / DWG / SLDDRW / PNG / JPG
            </div>
          </>
        )}
      </div>

      {/* オプション */}
      <div className="mt-6 flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={useAi}
            onChange={(e) => setUseAi(e.target.checked)}
            className="w-4 h-4 rounded accent-accent"
            disabled={checking}
          />
          <span>🏭 加工可能性チェック（AI）- 必須寸法の抜け・加工困難箇所を指摘</span>
        </label>

        <button
          onClick={() => file && onCheck(file)}
          disabled={!file || checking}
          className={`
            px-6 py-2.5 rounded-lg font-medium transition
            ${!file || checking
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-accent text-slate-900 hover:bg-cyan-300'}
          `}
        >
          {checking ? (
            <>
              <span className="inline-block animate-spin mr-2">⟳</span>
              検図中...
            </>
          ) : (
            '検図を実行 →'
          )}
        </button>
      </div>

      {error && (
        <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          ❌ {error}
        </div>
      )}

      {/* 使い方ヒント */}
      <div className="mt-8 p-4 rounded-lg bg-dark-surface/50 text-xs text-slate-400">
        <div className="font-medium text-slate-300 mb-2">💡 使い方</div>
        <ul className="space-y-1 ml-4 list-disc">
          <li>図面ファイルをドロップして「検図を実行」を押すだけ</li>
          <li>結果は PDF 上に赤ペン風の注釈で表示されます</li>
          <li>社内規格に合わせるには「サンプル学習」で合格図面を食わせてください</li>
          <li>加工可能性チェックは図面画像をGeminiに送って分析します（API利用・有料）</li>
        </ul>
      </div>
    </div>
  );
}
