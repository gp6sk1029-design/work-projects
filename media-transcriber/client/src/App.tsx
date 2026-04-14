import { useState, useRef, useCallback } from 'react';
import type { AppView, Recording, Transcription, SummaryData, Section, ChatMessage, MindmapData, MainTab, HistoryItem } from './types';
import FileUpload from './components/FileUpload';
import ProcessingStatus from './components/ProcessingStatus';
import TranscriptView from './components/TranscriptView';
import SummaryPanel from './components/SummaryPanel';
import MindmapRenderer from './components/MindmapRenderer';
import VideoSections from './components/VideoSections';
import VideoPlayer from './components/VideoPlayer';
import ChatPanel from './components/ChatPanel';
import AudioModeIndicator from './components/AudioModeIndicator';
import Sidebar from './components/Sidebar';
import ExportDialog from './components/ExportDialog';

export default function App() {
  // ビュー状態
  const [view, setView] = useState<AppView>('upload');
  const [activeTab, setActiveTab] = useState<MainTab>('transcript');

  // データ状態
  const [recording, setRecording] = useState<Recording | null>(null);
  const [transcription, setTranscription] = useState<Transcription | null>(null);
  const [summaries, setSummaries] = useState<SummaryData[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [mindmaps, setMindmaps] = useState<MindmapData[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  // 動画プレイヤーref
  const videoRef = useRef<HTMLVideoElement>(null);

  // タイムスタンプジャンプ
  const handleTimeJump = useCallback((time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
    }
  }, []);

  // アップロード完了
  const handleUploadComplete = (rec: Recording) => {
    setRecording(rec);
    setView('processing');
  };

  // 処理完了
  const handleProcessingComplete = (data: {
    transcription: Transcription;
    summaries: SummaryData[];
    sections: Section[];
    mindmaps: MindmapData[];
  }) => {
    setTranscription(data.transcription);
    setSummaries(data.summaries);
    setSections(data.sections);
    setMindmaps(data.mindmaps);
    setChatMessages([]);
    setView('result');
  };

  // 履歴から選択
  const handleSelectHistory = async (id: string) => {
    try {
      const res = await fetch(`/api/history/${id}`);
      const data = await res.json();
      setRecording(data.recording);
      setTranscription(data.transcription);
      setSummaries(data.summaries || []);
      setSections(data.sections || []);
      setChatMessages(data.chatMessages || []);
      setMindmaps(data.mindmaps || []);
      setView('result');
      setSidebarOpen(false);
    } catch (err) {
      console.error('履歴読み込みエラー:', err);
    }
  };

  // インポート（.mt.json.gz）
  const handleImport = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/import', { method: 'POST', body: formData });
      if (res.ok) {
        const { recordingId } = await res.json();
        await handleSelectHistory(recordingId);
      }
    } catch (err) {
      console.error('インポートエラー:', err);
    }
  };

  // 新規アップロードに戻る
  const handleNewUpload = () => {
    setView('upload');
    setRecording(null);
    setTranscription(null);
    setSummaries([]);
    setSections([]);
    setChatMessages([]);
    setMindmaps([]);
  };

  const tabs: { key: MainTab; label: string }[] = [
    { key: 'transcript', label: '文字起こし' },
    { key: 'summary', label: '要約' },
    { key: 'sections', label: 'セクション' },
    { key: 'mindmap', label: 'マインドマップ' },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      {/* サイドバー */}
      <Sidebar
        isOpen={sidebarOpen}
        history={history}
        setHistory={setHistory}
        onSelect={handleSelectHistory}
        onClose={() => setSidebarOpen(false)}
        onNewUpload={handleNewUpload}
      />

      {/* メインエリア */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* ヘッダー */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-dark-border bg-dark-surface">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-dark-hover rounded-lg transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-xl font-bold bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent">
              Media Transcriber
            </h1>
          </div>
          <div className="flex items-center gap-3">
            {recording && <AudioModeIndicator mode={recording.audio_mode} />}
            {view === 'result' && recording && (
              <button onClick={() => setExportOpen(true)} className="btn-primary text-sm flex items-center gap-1.5">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                保存
              </button>
            )}
            {view === 'result' && (
              <button onClick={handleNewUpload} className="btn-secondary text-sm">
                新規アップロード
              </button>
            )}
          </div>
        </header>

        {/* コンテンツ */}
        <div className="flex-1 flex overflow-hidden">
          {/* メインコンテンツ */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {view === 'upload' && (
              <div className="flex-1 flex items-center justify-center p-8">
                <FileUpload onUploadComplete={handleUploadComplete} onImport={handleImport} />
              </div>
            )}

            {view === 'processing' && recording && (
              <div className="flex-1 flex items-center justify-center p-8">
                <ProcessingStatus
                  recording={recording}
                  onComplete={handleProcessingComplete}
                />
              </div>
            )}

            {view === 'result' && recording && (
              <div className="flex-1 flex flex-col overflow-hidden">
                {/* 動画プレイヤー */}
                {recording.is_video && (
                  <div className="border-b border-dark-border">
                    <VideoPlayer
                      ref={videoRef}
                      src={`/uploads/${recording.file_name}`}
                      isVideo={recording.is_video}
                    />
                  </div>
                )}

                {/* タブ */}
                <div className="flex border-b border-dark-border px-6">
                  {tabs.map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key)}
                      className={`px-4 py-3 text-sm font-medium transition-colors ${
                        activeTab === tab.key ? 'tab-active' : 'tab-inactive'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* タブコンテンツ */}
                <div className="flex-1 overflow-auto p-6">
                  {activeTab === 'transcript' && transcription && (
                    <TranscriptView
                      transcription={transcription}
                      onTimeClick={handleTimeJump}
                      isVideo={recording.is_video}
                    />
                  )}
                  {activeTab === 'summary' && (
                    <SummaryPanel
                      recordingId={recording.id}
                      summaries={summaries}
                      onSummariesUpdate={setSummaries}
                    />
                  )}
                  {activeTab === 'sections' && (
                    <VideoSections
                      recordingId={recording.id}
                      sections={sections}
                      onSectionsUpdate={setSections}
                      onTimeClick={handleTimeJump}
                      isVideo={recording.is_video}
                    />
                  )}
                  {activeTab === 'mindmap' && (
                    <MindmapRenderer
                      recordingId={recording.id}
                      mindmaps={mindmaps}
                      onMindmapsUpdate={setMindmaps}
                    />
                  )}
                </div>
              </div>
            )}
          </div>

          {/* チャットパネル（結果表示時のみ） */}
          {view === 'result' && recording && transcription && (
            <div className="w-96 border-l border-dark-border flex flex-col">
              <ChatPanel
                recordingId={recording.id}
                messages={chatMessages}
                onMessagesUpdate={setChatMessages}
              />
            </div>
          )}
        </div>
      </div>
      {/* エクスポートダイアログ */}
      {exportOpen && recording && (
        <ExportDialog
          recordingId={recording.id}
          fileName={recording.file_name}
          onClose={() => setExportOpen(false)}
        />
      )}
    </div>
  );
}
