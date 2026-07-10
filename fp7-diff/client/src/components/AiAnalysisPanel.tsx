import type { AiSummary } from '../types';

interface Props {
  ai: AiSummary;
}

export default function AiAnalysisPanel({ ai }: Props) {
  const severityColor = {
    high: 'border-red-500 bg-red-900/20 text-red-300',
    medium: 'border-yellow-500 bg-yellow-900/20 text-yellow-300',
    low: 'border-blue-500 bg-blue-900/20 text-blue-300',
  };

  return (
    <div className="space-y-4">
      {/* Overview */}
      <div className="p-4 bg-dark-surface border-l-4 border-accent-500 rounded">
        <h3 className="text-sm font-semibold text-accent-400 mb-2">📋 全体所見</h3>
        <p className="text-gray-200 leading-relaxed">{ai.overview}</p>
      </div>

      {/* Main Changes */}
      {ai.mainChanges.length > 0 && (
        <div className="p-4 bg-dark-surface border border-dark-border rounded">
          <h3 className="text-sm font-semibold text-yellow-400 mb-3">🎯 主要な変更ポイント</h3>
          <div className="space-y-3">
            {ai.mainChanges.map((c, i) => (
              <div key={i} className="p-3 bg-dark-bg rounded border-l-2 border-yellow-500">
                <h4 className="font-semibold text-white mb-1">{i + 1}. {c.title}</h4>
                <p className="text-sm text-gray-300 mb-1">{c.description}</p>
                <p className="text-xs text-gray-400">
                  <span className="font-semibold">影響: </span>{c.impact}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Patterns */}
      {ai.patterns.length > 0 && (
        <div className="p-4 bg-dark-surface border border-dark-border rounded">
          <h3 className="text-sm font-semibold text-green-400 mb-3">🔍 検出された変更パターン</h3>
          <div className="space-y-2">
            {ai.patterns.map((p, i) => (
              <div key={i} className="p-3 bg-dark-bg rounded">
                <h4 className="font-semibold text-white text-sm mb-1">{p.name}</h4>
                <p className="text-xs text-gray-300 mb-1">{p.description}</p>
                {p.examples.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {p.examples.map((ex, j) => (
                      <span key={j} className="px-2 py-0.5 bg-dark-surface rounded text-xs font-mono text-accent-400">
                        {ex}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risks */}
      {ai.risks.length > 0 && (
        <div className="p-4 bg-dark-surface border border-dark-border rounded">
          <h3 className="text-sm font-semibold text-red-400 mb-3">⚠️ 横展開時のリスク</h3>
          <div className="space-y-2">
            {ai.risks.map((r, i) => (
              <div key={i} className={`p-3 border-l-4 rounded ${severityColor[r.severity]}`}>
                <p className="text-sm">
                  <span className="font-semibold uppercase mr-2">[{r.severity}]</span>
                  {r.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {ai.recommendations.length > 0 && (
        <div className="p-4 bg-dark-surface border border-dark-border rounded">
          <h3 className="text-sm font-semibold text-purple-400 mb-3">💡 推奨アクション</h3>
          <ul className="space-y-1.5">
            {ai.recommendations.map((r, i) => (
              <li key={i} className="text-sm text-gray-300 flex gap-2">
                <span className="text-purple-400">→</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
