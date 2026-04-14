import { useEffect, useState, useRef } from 'react';
import type { Recording, Transcription, SummaryData, Section, MindmapData, ProcessingStep } from '../types';

interface Props {
  recording: Recording;
  onComplete: (data: {
    transcription: Transcription;
    summaries: SummaryData[];
    sections: Section[];
    mindmaps: MindmapData[];
  }) => void;
}

export default function ProcessingStatus({ recording, onComplete }: Props) {
  const [steps, setSteps] = useState<ProcessingStep[]>([
    { step: 'transcribe', status: 'waiting', message: 'AI文字起こし（数分かかります）' },
    { step: 'summarize', status: 'waiting', message: '要約生成' },
    { step: 'sections', status: 'waiting', message: 'セクション分割' },
    { step: 'mindmap', status: 'waiting', message: 'マインドマップ生成' },
  ]);
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    runProcessing();
  }, []);

  const updateStep = (stepName: string, update: Partial<ProcessingStep>) => {
    setSteps(prev => prev.map(s => s.step === stepName ? { ...s, ...update } : s));
  };

  async function runProcessing() {
    try {
      // Step 1: 文字起こし（通常のPOST、長時間待機）
      updateStep('transcribe', { status: 'processing', message: 'AI文字起こし中...（32分の動画で3〜5分程度）' });

      const transRes = await fetch('/api/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recordingId: recording.id }),
      });

      if (!transRes.ok) {
        const err = await transRes.json();
        throw new Error(err.error || '文字起こしに失敗しました');
      }

      const transcription: Transcription = await transRes.json();
      updateStep('transcribe', { status: 'done', message: '文字起こし完了' });

      // Step 2: 要約（簡潔版）
      updateStep('summarize', { status: 'processing', message: '簡潔要約を生成中...' });
      let summaries: SummaryData[] = [];
      try {
        const sumRes = await fetch('/api/summarize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ recordingId: recording.id, type: 'brief' }),
        });
        if (sumRes.ok) {
          summaries = [await sumRes.json()];
        }
      } catch {}
      updateStep('summarize', { status: 'done', message: '要約完了' });

      // Step 3: セクション分割
      updateStep('sections', { status: 'processing', message: 'セクション分割中...' });
      let sections: Section[] = [];
      try {
        const secRes = await fetch('/api/sections', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ recordingId: recording.id }),
        });
        if (secRes.ok) {
          sections = await secRes.json();
        }
      } catch {}
      updateStep('sections', { status: 'done', message: 'セクション分割完了' });

      // Step 4: マインドマップ
      updateStep('mindmap', { status: 'processing', message: 'マインドマップ生成中...' });
      let mindmaps: MindmapData[] = [];
      try {
        const mmRes = await fetch('/api/mindmap', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ recordingId: recording.id }),
        });
        if (mmRes.ok) {
          mindmaps = [await mmRes.json()];
        }
      } catch {}
      updateStep('mindmap', { status: 'done', message: 'マインドマップ完了' });

      onComplete({ transcription, summaries, sections, mindmaps });
    } catch (err: any) {
      console.error('処理エラー:', err);
      setError(err.message || '処理に失敗しました');
    }
  }

  const statusIcon = (status: ProcessingStep['status']) => {
    switch (status) {
      case 'waiting': return <div className="w-6 h-6 rounded-full border-2 border-gray-600" />;
      case 'processing': return <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />;
      case 'done': return (
        <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      );
      case 'error': return (
        <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      );
    }
  };

  return (
    <div className="w-full max-w-lg">
      <div className="card p-8">
        <h2 className="text-lg font-bold mb-6 text-center">処理中...</h2>
        <p className="text-sm text-gray-400 text-center mb-2">{recording.file_name}</p>
        <p className="text-xs text-gray-500 text-center mb-6">
          {Math.round(recording.duration_seconds / 60)}分の{recording.is_video ? '動画' : '音声'}
        </p>

        <div className="space-y-4">
          {steps.map((step) => (
            <div key={step.step} className="flex items-center gap-4">
              {statusIcon(step.status)}
              <p className={`text-sm ${step.status === 'processing' ? 'text-white' : 'text-gray-400'}`}>
                {step.message}
              </p>
            </div>
          ))}
        </div>

        {error && (
          <div className="mt-6 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
