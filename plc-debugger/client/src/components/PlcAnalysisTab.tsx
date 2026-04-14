import type { AnalysisIssue } from '../types';
import IssueCard from './IssueCard';

interface Props {
  issues: AnalysisIssue[];
  onConsult?: (issue: AnalysisIssue) => void;
}

export default function PlcAnalysisTab({ issues, onConsult }: Props) {
  if (issues.length === 0) {
    return (
      <div className="text-center text-gray-500 py-12">
        <p className="text-lg">PLC関連の問題は検出されませんでした</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold text-gray-300 mb-2">
        PLC プログラム分析結果 ({issues.length}件)
      </h2>
      {issues.map((issue) => (
        <IssueCard key={issue.id} issue={issue} onConsult={onConsult} />
      ))}
    </div>
  );
}
