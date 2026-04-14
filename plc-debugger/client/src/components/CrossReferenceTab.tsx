import type { AnalysisIssue, AnalysisResult } from '../types';
import IssueCard from './IssueCard';

interface Props {
  issues: AnalysisIssue[];
  hmiAnalysis?: AnalysisResult['hmiAnalysis'];
}

export default function CrossReferenceTab({ issues, hmiAnalysis }: Props) {
  return (
    <div className="space-y-6">
      {/* クロスリファレンスサマリー */}
      {hmiAnalysis && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-dark-surface rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">変数バインド状況</h3>
            <div className="space-y-2 text-sm">
              <StatRow label="HMIで使用中のPLC変数" value={hmiAnalysis.crossReference.plcVariablesUsedInHmi} color="text-green-400" />
              <StatRow label="HMI未使用のPLC変数" value={hmiAnalysis.crossReference.plcVariablesNotInHmi} color="text-gray-400" />
              <StatRow label="PLC未定義のHMI変数" value={hmiAnalysis.crossReference.hmiVariablesNotInPlc} color="text-severity-warning" />
              <StatRow label="型不一致" value={hmiAnalysis.crossReference.unmatchedTypes} color="text-severity-critical" />
            </div>
          </div>

          <div className="bg-dark-surface rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">アラームカバレッジ</h3>
            <div className="space-y-2 text-sm">
              <StatRow label="PLCエラーフラグ" value={hmiAnalysis.alarmCoverage.plcErrorFlags} color="text-gray-300" />
              <StatRow label="HMIアラーム定義済み" value={hmiAnalysis.alarmCoverage.hmiAlarmsDefined} color="text-green-400" />
              <StatRow label="未カバー" value={hmiAnalysis.alarmCoverage.uncoveredErrors.length} color="text-severity-critical" />
            </div>
            {hmiAnalysis.alarmCoverage.uncoveredErrors.length > 0 && (
              <div className="mt-3 p-2 bg-severity-critical/10 rounded">
                <p className="text-xs text-severity-critical font-medium mb-1">未カバーのエラー:</p>
                <ul className="text-xs text-gray-400 space-y-1">
                  {hmiAnalysis.alarmCoverage.uncoveredErrors.map((e) => (
                    <li key={e} className="font-mono">{e}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Issue一覧 */}
      {issues.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-300">
            PLC↔HMI 整合性の問題 ({issues.length}件)
          </h2>
          {issues.map((issue) => (
            <IssueCard key={issue.id} issue={issue} />
          ))}
        </div>
      ) : (
        <p className="text-center text-gray-500 py-8">クロスリファレンスの問題は検出されませんでした</p>
      )}
    </div>
  );
}

function StatRow({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{label}</span>
      <span className={`font-bold ${color}`}>{value}</span>
    </div>
  );
}
