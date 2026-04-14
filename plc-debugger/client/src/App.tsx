import { useState } from 'react';
import type { ProjectData, TabId, ChatMessage, AnalysisIssue } from './types';
import Sidebar from './components/Sidebar';
import FileUpload from './components/FileUpload';
import AnalysisResult from './components/AnalysisResult';
import ProgramGenerateTab from './components/ProgramGenerateTab';
import TroubleshootChat from './components/TroubleshootChat';
import HelpGuide from './components/HelpGuide';
import DiagnosisModal from './components/DiagnosisModal';

export default function App() {
  const [projectData, setProjectData] = useState<ProjectData | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('plc');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isAnalyzingProgram, setIsAnalyzingProgram] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showDiagnosisModal, setShowDiagnosisModal] = useState(false);
  const [isDiagnosing, setIsDiagnosing] = useState(false);

  const handleFilesUploaded = async (files: File[]) => {
    setIsAnalyzing(true);
    try {
      const formData = new FormData();
      files.forEach((f) => formData.append('files', f));

      const res = await fetch('/api/upload', { method: 'POST', body: formData });
      const data = await res.json();
      setProjectData(data);
    } catch (err) {
      console.error('アップロードエラー:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAnalyze = async () => {
    if (!projectData) return;
    setIsAnalyzing(true);
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId: projectData.projectId }),
      });
      if (!res.ok) {
        const err = await res.json();
        console.error('分析APIエラー:', err);
        return;
      }
      const result = await res.json();
      setProjectData((prev) => (prev ? { ...prev, analysisResult: result } : null));
    } catch (err) {
      console.error('分析エラー:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAnalyzeProgram = async () => {
    if (!projectData) return;
    setIsAnalyzingProgram(true);
    try {
      const res = await fetch('/api/analyze-program', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId: projectData.projectId }),
      });
      if (!res.ok) {
        const err = await res.json();
        console.error('プログラム解析APIエラー:', err);
        return;
      }
      const result = await res.json();
      setProjectData((prev) => (prev ? { ...prev, programAnalysis: result } : null));
      setActiveTab('programAnalysis');
    } catch (err) {
      console.error('プログラム解析エラー:', err);
    } finally {
      setIsAnalyzingProgram(false);
    }
  };

  const handleDiagnosis = async (images: string[]) => {
    if (!projectData) return;
    setIsDiagnosing(true);
    try {
      const res = await fetch('/api/diagnosis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId: projectData.projectId,
          images,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        console.error('総合診断APIエラー:', err);
        return;
      }
      const result = await res.json();
      setProjectData((prev) => (prev ? { ...prev, diagnosisResult: result } : null));
      setActiveTab('diagnosis');
      setShowDiagnosisModal(false);
    } catch (err) {
      console.error('総合診断エラー:', err);
    } finally {
      setIsDiagnosing(false);
    }
  };

  const handleConsult = (issue: AnalysisIssue) => {
    const severityLabel = { critical: '🔴 CRITICAL', warning: '🟡 WARNING', info: '🔵 INFO' }[issue.severity];
    const message = `【${severityLabel}】${issue.id} についてAIに相談します。

■ 問題: ${issue.description}
■ 場所: ${issue.location}
■ カテゴリ: ${issue.category}
${issue.suggestion ? `■ 改善提案: ${issue.suggestion}` : ''}
${issue.relatedVariables?.length ? `■ 関連変数: ${issue.relatedVariables.join(', ')}` : ''}

この問題の原因と具体的な対策を詳しく教えてください。`;
    handleSendMessage(message);
  };

  const handleSendMessage = async (message: string, images?: string[]) => {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      images,
      timestamp: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, userMsg]);

    try {
      const res = await fetch('/api/troubleshoot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          images,
          history: chatMessages,
          projectId: projectData?.projectId,
        }),
      });
      const data = await res.json();
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('チャットエラー:', err);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-dark-bg text-gray-100">
      {/* 左サイドバー */}
      <Sidebar
        projectData={projectData}
        onAnalyze={handleAnalyze}
        isAnalyzing={isAnalyzing}
        onAnalyzeProgram={handleAnalyzeProgram}
        isAnalyzingProgram={isAnalyzingProgram}
        onDiagnosis={() => setShowDiagnosisModal(true)}
        isDiagnosing={isDiagnosing}
        onShowHelp={() => setShowHelp(true)}
      />

      {/* メインエリア */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden border-x border-dark-border">
        {!projectData ? (
          <div className="flex flex-col h-full">
            {/* アップロード前でもプログラム生成タブを表示 */}
            <div className="flex border-b border-dark-border bg-dark-surface">
              <button
                onClick={() => setActiveTab('plc')}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
                  activeTab !== 'generate' ? 'text-plc border-plc' : 'text-gray-400 border-transparent hover:text-gray-200'
                }`}
              >
                ファイル解析
              </button>
              <button
                onClick={() => setActiveTab('generate')}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
                  activeTab === 'generate' ? 'text-green-400 border-green-400' : 'text-gray-400 border-transparent hover:text-gray-200'
                }`}
              >
                プログラム生成
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {activeTab === 'generate' ? (
                <div className="p-4">
                  <ProgramGenerateTab />
                </div>
              ) : (
                <FileUpload onFilesUploaded={handleFilesUploaded} isUploading={isAnalyzing} />
              )}
            </div>
          </div>
        ) : (
          <AnalysisResult
            projectData={projectData}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            isAnalyzing={isAnalyzing}
            onConsult={handleConsult}
            onConsultMessage={handleSendMessage}
          />
        )}
      </main>

      {/* 右チャットパネル */}
      <TroubleshootChat
        messages={chatMessages}
        onSendMessage={handleSendMessage}
        hasProject={!!projectData}
      />

      {/* ヘルプモーダル */}
      {showHelp && <HelpGuide onClose={() => setShowHelp(false)} />}

      {/* 総合診断モーダル */}
      {showDiagnosisModal && (
        <DiagnosisModal
          onSubmit={handleDiagnosis}
          onClose={() => !isDiagnosing && setShowDiagnosisModal(false)}
          isDiagnosing={isDiagnosing}
        />
      )}
    </div>
  );
}
