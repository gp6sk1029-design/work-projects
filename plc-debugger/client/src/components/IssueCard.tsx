import { useState } from 'react';
import type { AnalysisIssue } from '../types';

interface Props {
  issue: AnalysisIssue;
  onConsult?: (issue: AnalysisIssue) => void;
}

const SEVERITY_CONFIG = {
  critical: { bg: 'bg-severity-critical/10', border: 'border-severity-critical/30', text: 'text-severity-critical', label: 'CRITICAL' },
  warning: { bg: 'bg-severity-warning/10', border: 'border-severity-warning/30', text: 'text-severity-warning', label: 'WARNING' },
  info: { bg: 'bg-severity-info/10', border: 'border-severity-info/30', text: 'text-severity-info', label: 'INFO' },
};

const DOMAIN_CONFIG = {
  plc: { bg: 'bg-plc/20', text: 'text-plc', label: 'PLC' },
  hmi: { bg: 'bg-hmi/20', text: 'text-hmi', label: 'HMI' },
  'hmi-plc-cross': { bg: 'bg-cross/20', text: 'text-cross', label: 'PLC\u2194HMI' },
};

export default function IssueCard({ issue, onConsult }: Props) {
  const [expanded, setExpanded] = useState(false);
  const sev = SEVERITY_CONFIG[issue.severity];
  const dom = DOMAIN_CONFIG[issue.domain];

  return (
    <div
      className={`${sev.bg} border ${sev.border} rounded-lg p-4 cursor-pointer transition hover:brightness-110`}
      onClick={() => setExpanded(!expanded)}
    >
      {/* ヘッダー */}
      <div className="flex items-start gap-3">
        <div className="flex flex-col gap-1 flex-shrink-0">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${sev.bg} ${sev.text}`}>{sev.label}</span>
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${dom.bg} ${dom.text}`}>{dom.label}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500 font-mono">{issue.id}</span>
            <span className="text-xs text-gray-400">{issue.category}</span>
          </div>
          <p className="text-sm text-white">{issue.description}</p>
          <p className="text-xs text-gray-400 mt-1">{issue.location}</p>
        </div>
        <span className="text-gray-500 text-xs flex-shrink-0">{expanded ? '\u25B2' : '\u25BC'}</span>
      </div>

      {/* 展開部分 */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-dark-border space-y-3">
          <div>
            <h4 className="text-xs font-semibold text-gray-400 mb-1">改善提案</h4>
            <p className="text-sm text-gray-200">{issue.suggestion}</p>
          </div>

          {issue.relatedVariables && issue.relatedVariables.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-400 mb-1">関連変数</h4>
              <div className="flex flex-wrap gap-1">
                {issue.relatedVariables.map((v) => (
                  <span key={v} className="px-2 py-0.5 bg-dark-bg rounded text-xs font-mono text-gray-300">{v}</span>
                ))}
              </div>
            </div>
          )}

          {issue.relatedScreens && issue.relatedScreens.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-400 mb-1">関連画面</h4>
              <div className="flex flex-wrap gap-1">
                {issue.relatedScreens.map((s) => (
                  <span key={s} className="px-2 py-0.5 bg-hmi/10 rounded text-xs text-hmi">{s}</span>
                ))}
              </div>
            </div>
          )}

          {issue.reference && (
            <p className="text-xs text-gray-500">参考: {issue.reference}</p>
          )}

          {/* AIに相談ボタン */}
          {onConsult && (
            <button
              onClick={(e) => { e.stopPropagation(); onConsult(issue); }}
              className="w-full mt-2 px-3 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-xs font-bold text-white transition flex items-center justify-center gap-2"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              この問題をAIに相談する
            </button>
          )}
        </div>
      )}
    </div>
  );
}
