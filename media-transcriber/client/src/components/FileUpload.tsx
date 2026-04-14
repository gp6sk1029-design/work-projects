import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import type { Recording } from '../types';

interface Props {
  onUploadComplete: (recording: Recording) => void;
  onImport?: (file: File) => void;
}

export default function FileUpload({ onUploadComplete, onImport }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'アップロードに失敗しました');
      }

      const recording = await res.json();
      onUploadComplete(recording);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }, [onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a', '.wma'],
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.3gpp', '.flv'],
    },
    maxFiles: 1,
    maxSize: 2 * 1024 * 1024 * 1024, // 2GB
    disabled: uploading,
  });

  return (
    <div className="w-full max-w-2xl">
      <div
        {...getRootProps()}
        className={`card p-12 text-center cursor-pointer transition-all border-2 border-dashed ${
          isDragActive
            ? 'border-accent-blue bg-accent-blue/10'
            : uploading
              ? 'border-dark-border opacity-50 cursor-not-allowed'
              : 'border-dark-border hover:border-accent-blue/50 hover:bg-dark-hover'
        }`}
      >
        <input {...getInputProps()} />

        <div className="mb-4">
          <svg className="w-16 h-16 mx-auto text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>

        {uploading ? (
          <div>
            <div className="animate-spin w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full mx-auto mb-3" />
            <p className="text-gray-400">アップロード中...</p>
          </div>
        ) : isDragActive ? (
          <p className="text-accent-blue text-lg">ここにドロップしてください</p>
        ) : (
          <>
            <p className="text-lg mb-2">音声・動画ファイルをドラッグ&ドロップ</p>
            <p className="text-sm text-gray-500">
              またはクリックしてファイルを選択
            </p>
            <p className="text-xs text-gray-600 mt-3">
              対応形式: MP3, WAV, AAC, OGG, FLAC, MP4, MOV, AVI, MKV, WEBM (最大2GB)
            </p>
          </>
        )}
      </div>

      {/* インポートボタン */}
      {onImport && (
        <div className="mt-4 text-center">
          <label className="inline-flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-gray-200 cursor-pointer transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            過去の保存ファイルを読み込む (.mt.json.gz)
            <input
              type="file"
              accept=".gz,.json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onImport(file);
              }}
            />
          </label>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-accent-red/10 border border-accent-red/30 rounded-lg text-accent-red text-sm">
          {error}
        </div>
      )}
    </div>
  );
}
