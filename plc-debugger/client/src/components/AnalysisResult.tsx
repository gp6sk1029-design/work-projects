import type { ProjectData, TabId, AnalysisIssue } from '../types';
import PlcAnalysisTab from './PlcAnalysisTab';
import HmiAnalysisTab from './HmiAnalysisTab';
import CrossReferenceTab from './CrossReferenceTab';
import ScreenTransitionTab from './ScreenTransitionTab';
import ScreenshotAnalysisTab from './ScreenshotAnalysisTab';
import ProgramGenerateTab from './ProgramGenerateTab';
import ProgramAnalysisTab from './ProgramAnalysisTab';
import DiagnosisResultTab from './DiagnosisResultTab';
import { exportIssuesToCsv } from '../hooks/useAnalysis';

interface Props {
  projectData: ProjectData;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  isAnalyzing: boolean;
  onConsult?: (issue: AnalysisIssue) => void;
  onConsultMessage?: (message: string) => void;
}

const TABS: { id: TabId; label: string; color: string }[] = [
  { id: 'programAnalysis', label: 'プログラム解析', color: 'text-blue-400 border-blue-400' },
  { id: 'plc', label: 'PLC分析', color: 'text-plc border-plc' },
  { id: 'hmi', label: 'HMI分析', color: 'text-hmi border-hmi' },
  { id: 'crossref', label: 'クロスリファレンス', color: 'text-cross border-cross' },
  { id: 'transition', label: '画面遷移図', color: 'text-hmi border-hmi' },
  { id: 'diagnosis', label: '総合診断', color: 'text-purple-400 border-purple-400' },
  { id: 'screenshot', label: 'スクリーンショット', color: 'text-purple-300 border-purple-300' },
  { id: 'generate', label: 'プログラム生成', color: 'text-green-400 border-green-400' },
];

export default function AnalysisResult({ projectData, activeTab, onTabChange, isAnalyzing, onConsult, onConsultMessage }: Props) {
  const result = projectData.analysisResult;

  return (
    <div className="flex flex-col h-full">
      {/* タブバー */}
      <div className="flex border-b border-dark-border bg-dark-surface">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
              activeTab === tab.id
                ? tab.color
                : 'text-gray-400 border-transparent hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 統計サマリー */}
      {result && (
        <div className="flex gap-4 p-4 bg-dark-surface/50 border-b border-dark-border">
          <StatBadge label="Critical" count={result.statistics.critical} color="bg-severity-critical" />
          <StatBadge label="Warning" count={result.statistics.warning} color="bg-severity-warning" />
          <StatBadge label="Info" count={result.statistics.info} color="bg-severity-info" />
          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={() => exportIssuesToCsv(result)}
              className="px-3 py-1 bg-dark-hover hover:bg-dark-border rounded text-xs text-gray-300 transition"
            >
              CSV出力
            </button>
            <span className="text-xs text-gray-400">
              信頼度: <span className="text-white">{result.projectSummary.analysisConfidence}</span>
            </span>
          </div>
        </div>
      )}

      {/* タブコンテンツ */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'diagnosis' && projectData.diagnosisResult ? (
          <DiagnosisResultTab result={projectData.diagnosisResult} onConsult={onConsultMessage} />
        ) : activeTab === 'diagnosis' ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">総合診断結果がありません</p>
              <p className="text-sm">左パネルの「🔍 総合診断」ボタンを押してください</p>
            </div>
          </div>
        ) : activeTab === 'programAnalysis' && projectData.programAnalysis ? (
          <ProgramAnalysisTab
            overview={projectData.programAnalysis.overview}
            sections={projectData.programAnalysis.sections}
          />
        ) : activeTab === 'programAnalysis' ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">プログラム解析結果がありません</p>
              <p className="text-sm">左パネルの「📊 プログラム解析」ボタンを押してください</p>
            </div>
          </div>
        ) : activeTab === 'generate' ? (
          <ProgramGenerateTab />
        ) : isAnalyzing ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin w-8 h-8 border-2 border-plc border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-gray-400">Claude AI が分析中...</p>
            </div>
          </div>
        ) : !result ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">分析結果がありません</p>
              <p className="text-sm">左パネルの「バグ分析実行」ボタンを押してください</p>
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'plc' && <PlcAnalysisTab issues={result.issues.filter((i) => i.domain === 'plc')} onConsult={onConsult} />}
            {activeTab === 'hmi' && <HmiAnalysisTab issues={result.issues.filter((i) => i.domain === 'hmi')} onConsult={onConsult} />}
            {activeTab === 'crossref' && (
              <CrossReferenceTab
                issues={result.issues.filter((i) => i.domain === 'hmi-plc-cross')}
                hmiAnalysis={result.hmiAnalysis}
              />
            )}
            {activeTab === 'transition' && (
              <ScreenTransitionTab diagram={result.hmiAnalysis?.screenTransitionDiagram} />
            )}
            {activeTab === 'screenshot' && (
              <ScreenshotAnalysisTab analyses={projectData.screenshotAnalyses} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

function StatBadge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-3 h-3 rounded-full ${color}`} />
      <span className="text-xs text-gray-300">
        {label}: <span className="text-white font-bold">{count}</span>
      </span>
    </div>
  );
}
