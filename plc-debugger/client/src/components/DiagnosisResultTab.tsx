import { useState } from 'react';
import type { ComprehensiveDiagnosisResult, Countermeasure } from '../types';

interface Props {
  result: ComprehensiveDiagnosisResult;
  onConsult?: (message: string) => void;
}

export default function DiagnosisResultTab({ result, onConsult }: Props) {
  const [expandedFixes, setExpandedFixes] = useState<Set<string>>(new Set());

  const toggleFix = (id: string) => {
    setExpandedFixes((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const probabilityBadge = (p: 'high' | 'medium' | 'low') => {
    const styles = {
      high: 'bg-red-500/20 text-red-400 border-red-500/30',
      medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    };
    const labels = { high: '高', medium: '中', low: '低' };
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${styles[p]}`}>
        可能性: {labels[p]}
      </span>
    );
  };

  const priorityStyle = (p: 1 | 2 | 3) => {
    const styles = {
      1: 'border-l-red-500 bg-red-500/5',
      2: 'border-l-yellow-500 bg-yellow-500/5',
      3: 'border-l-blue-500 bg-blue-500/5',
    };
    const labels = { 1: '最優先', 2: '推奨', 3: '改善' };
    const colors = { 1: 'text-red-400', 2: 'text-yellow-400', 3: 'text-blue-400' };
    return { className: styles[p], label: labels[p], color: colors[p] };
  };

  const handleConsultFix = (fix: Countermeasure) => {
    if (!onConsult) return;
    const priorityLabel = { 1: '最優先', 2: '推奨', 3: '改善' }[fix.priority];
    const msg = `【総合診断 対策相談】${fix.id} — ${fix.title}

■ 優先度: ${priorityLabel}
■ 対策内容: ${fix.description}
■ 実装手順: ${fix.implementation}
■ リスク: ${fix.risk}
■ 関連原因: ${fix.relatedCauses.join(', ')}

この対策の実装方法をもっと具体的に教えてください。コード例も含めてお願いします。`;
    onConsult(msg);
  };

  return (
    <div className="space-y-6">
      {/* 総合所見 */}
      <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
        <h3 className="text-sm font-bold text-purple-300 mb-2 flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          総合所見
        </h3>
        <p className="text-sm text-gray-300 whitespace-pre-wrap">{result.summary}</p>
      </div>

      {/* セクション1: 検出された現象 */}
      {result.phenomena.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <span className="w-6 h-6 rounded bg-purple-600 text-white text-xs font-bold flex items-center justify-center">1</span>
            検出された現象（{result.phenomena.length}件）
          </h3>
          <div className="space-y-2">
            {result.phenomena.map((p) => (
              <div key={p.id} className="bg-dark-bg rounded-lg p-3 border border-purple-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-purple-400 font-mono text-xs">{p.id}</span>
                  <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px] font-bold border border-purple-500/30">
                    画像 {p.screenshotIndex + 1}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-dark-surface text-gray-300 text-[10px] font-bold">
                    {p.errorType}
                  </span>
                  {p.errorCode && (
                    <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-300 text-[10px] font-mono">
                      {p.errorCode}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-300">{p.description}</p>
                {p.affectedDevice && (
                  <p className="text-xs text-gray-500 mt-1">影響デバイス: {p.affectedDevice}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* セクション2: 原因分析 */}
      {result.rootCauseAnalysis.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <span className="w-6 h-6 rounded bg-orange-600 text-white text-xs font-bold flex items-center justify-center">2</span>
            原因分析（{result.rootCauseAnalysis.length}件）
          </h3>
          <div className="space-y-2">
            {result.rootCauseAnalysis.map((rca) => (
              <div key={rca.id} className="bg-dark-bg rounded-lg p-3 border border-dark-border">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-orange-400 font-mono text-xs">{rca.id}</span>
                  {probabilityBadge(rca.probability)}
                  <span className="text-[10px] text-gray-500">
                    → {rca.relatedPhenomena.join(', ')}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mb-1 font-mono">{rca.location}</p>
                <p className="text-sm text-gray-300">{rca.description}</p>
                {rca.relatedVariables && rca.relatedVariables.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {rca.relatedVariables.map((v) => (
                      <span key={v} className="px-1.5 py-0.5 rounded bg-dark-surface text-gray-400 text-[10px] font-mono">
                        {v}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* セクション3: 対策案 */}
      {result.countermeasures.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <span className="w-6 h-6 rounded bg-green-600 text-white text-xs font-bold flex items-center justify-center">3</span>
            対策案（{result.countermeasures.length}件）
          </h3>
          <div className="space-y-2">
            {result.countermeasures.map((fix) => {
              const ps = priorityStyle(fix.priority);
              const isExpanded = expandedFixes.has(fix.id);
              return (
                <div
                  key={fix.id}
                  className={`bg-dark-bg rounded-lg border border-dark-border border-l-4 ${ps.className} overflow-hidden`}
                >
                  <button
                    onClick={() => toggleFix(fix.id)}
                    className="w-full text-left p-3"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-bold ${ps.color}`}>{ps.label}</span>
                      <span className="text-green-400 font-mono text-xs">{fix.id}</span>
                      <span className="text-[10px] text-gray-500">
                        → {fix.relatedCauses.join(', ')}
                      </span>
                      <svg className={`w-3.5 h-3.5 ml-auto text-gray-500 transition ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                    <p className="text-sm text-white font-medium">{fix.title}</p>
                    <p className="text-xs text-gray-400 mt-1">{fix.description}</p>
                  </button>

                  {isExpanded && (
                    <div className="px-3 pb-3 space-y-3 border-t border-dark-border pt-3">
                      <div>
                        <p className="text-[10px] text-gray-500 font-bold mb-1">実装手順</p>
                        <p className="text-xs text-gray-300 whitespace-pre-wrap bg-dark-surface rounded p-2">{fix.implementation}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-gray-500 font-bold mb-1">リスク・注意点</p>
                        <p className="text-xs text-yellow-300/80">{fix.risk}</p>
                      </div>
                      {onConsult && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleConsultFix(fix); }}
                          className="w-full px-3 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-xs font-bold text-white transition flex items-center justify-center gap-1.5"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                          </svg>
                          この対策をAIに相談する
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
