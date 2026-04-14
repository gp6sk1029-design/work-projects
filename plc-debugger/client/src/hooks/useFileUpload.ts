import { useState, useCallback } from 'react';

export function useFileUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadFiles = useCallback(async (files: File[]) => {
    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      files.forEach((f) => formData.append('files', f));

      const res = await fetch('/api/upload', { method: 'POST', body: formData });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'アップロード失敗');
      }

      return await res.json();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'アップロードエラー';
      setError(msg);
      throw err;
    } finally {
      setIsUploading(false);
    }
  }, []);

  return { uploadFiles, isUploading, error };
}
