import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface Props {
  onFilesUploaded: (files: File[]) => void;
  isUploading: boolean;
}

const ACCEPTED_EXTENSIONS: Record<string, string[]> = {
  'application/zip': ['.smc2'],
  'text/csv': ['.csv'],
  'text/plain': ['.txt', '.st'],
  'application/pdf': ['.pdf'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
};

export default function FileUpload({ onFilesUploaded, isUploading }: Props) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFilesUploaded(acceptedFiles);
      }
    },
    [onFilesUploaded],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_EXTENSIONS,
    maxSize: 50 * 1024 * 1024,
    disabled: isUploading,
  });

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div
        {...getRootProps()}
        className={`w-full max-w-2xl border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
          isDragActive
            ? 'border-plc bg-plc/10'
            : 'border-dark-border hover:border-gray-500 hover:bg-dark-hover'
        } ${isUploading ? 'opacity-50 pointer-events-none' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="text-5xl mb-4">{isDragActive ? '\u{1F4E5}' : '\u{1F4C1}'}</div>
        {isUploading ? (
          <div>
            <p className="text-lg text-white mb-2">ファイルを解析中...</p>
            <div className="w-48 h-1 mx-auto bg-dark-border rounded overflow-hidden">
              <div className="h-full bg-plc animate-pulse rounded" style={{ width: '60%' }} />
            </div>
          </div>
        ) : (
          <>
            <p className="text-lg text-white mb-2">
              {isDragActive ? 'ファイルをドロップ' : 'ファイルをドラッグ&ドロップ'}
            </p>
            <p className="text-sm text-gray-400 mb-4">またはクリックしてファイルを選択</p>
            <div className="flex flex-wrap justify-center gap-2">
              {['.smc2', '.csv', '.txt/.st', '.pdf', '.png/.jpg'].map((ext) => (
                <span key={ext} className="px-2 py-1 bg-dark-surface rounded text-xs text-gray-300">
                  {ext}
                </span>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-4">
              .smc2 は最大50MB / 画像は5MB/枚 / その他20MB
            </p>
          </>
        )}
      </div>
    </div>
  );
}
