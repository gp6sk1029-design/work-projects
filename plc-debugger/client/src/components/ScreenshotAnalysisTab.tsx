import type { ScreenshotAnalysis } from '../types';

interface Props {
  analyses?: ScreenshotAnalysis[];
}

export default function ScreenshotAnalysisTab({ analyses }: Props) {
  if (!analyses || analyses.length === 0) {
    return (
      <div className="text-center text-gray-500 py-12">
        <p className="text-lg mb-2">スクリーンショット分析結果がありません</p>
        <p className="text-sm">HMI画面のスクリーンショット（.png/.jpg）をアップロードしてください</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {analyses.map((analysis, idx) => (
        <div key={idx} className="bg-dark-surface rounded-lg p-4 space-y-4">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-white">{analysis.screenName}</h3>
            <span className="text-xs text-gray-400">{analysis.fileName}</span>
          </div>

          {/* 検出された要素 */}
          {analysis.detectedElements.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-400 mb-2">検出された要素</h4>
              <div className="grid grid-cols-2 gap-2">
                {analysis.detectedElements.map((el, i) => (
                  <div key={i} className="bg-dark-bg rounded p-2 text-xs">
                    <span className="text-hmi">{el.type}</span>
                    <span className="text-gray-400 mx-1">-</span>
                    <span className="text-white">{el.label}</span>
                    {el.state && <span className="text-gray-500 ml-1">({el.state})</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 問題点 */}
          {[
            { label: 'レイアウト問題', items: analysis.layoutIssues, color: 'text-severity-warning' },
            { label: 'UX問題', items: analysis.uxIssues, color: 'text-severity-info' },
            { label: '安全性問題', items: analysis.safetyIssues, color: 'text-severity-critical' },
          ].map(
            ({ label, items, color }) =>
              items.length > 0 && (
                <div key={label}>
                  <h4 className={`text-xs font-semibold ${color} mb-1`}>{label}</h4>
                  <ul className="text-xs text-gray-300 space-y-1">
                    {items.map((item, i) => (
                      <li key={i}>- {item}</li>
                    ))}
                  </ul>
                </div>
              ),
          )}
        </div>
      ))}
    </div>
  );
}
