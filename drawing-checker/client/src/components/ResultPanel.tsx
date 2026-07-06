import type { CheckResponse, Finding, Severity } from '../types';

interface Props {
  response: CheckResponse;
  onReset: () => void;
  selectedIndex: number | null;
  onSelectFinding: (i: number | null) => void;
}

const SEVERITY_META: Record<Severity, { icon: string; bg: string; border: string; text: string; label: string }> = {
  error:   { icon: '❌', bg: 'bg-red-500/10',    border: 'border-red-500/40',    text: 'text-red-400',    label: 'ERROR' },
  warning: { icon: '⚠️', bg: 'bg-amber-500/10',  border: 'border-amber-500/40',  text: 'text-amber-400',  label: 'WARN'  },
  info:    { icon: 'ℹ️', bg: 'bg-blue-500/10',   border: 'border-blue-500/40',   text: 'text-blue-400',   label: 'INFO'  },
};

export default function ResultPanel({ response, onReset, selectedIndex, onSelectFinding }: Props) {
  const r = response.result;

  return (
    <div className="space-y-4">
      {/* サマリー */}
      <div className={`rounded-xl p-5 border ${r.pass ? 'bg-emerald-500/10 border-emerald-500/40' : 'bg-red-500/10 border-red-500/40'}`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="text-3xl">{r.pass ? '✅' : '❌'}</div>
            <div>
              <div className="text-xl font-bold">{r.pass ? '合格' : '不合格'}</div>
              <div className="text-xs text-slate-400">{r.drawing_name}</div>
            </div>
          </div>
          <div className="text-right text-xs text-slate-400">
            処理時間 {r.processing_time_sec.toFixed(2)}秒
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center mt-3">
          <div className="bg-red-500/20 rounded-lg py-2">
            <div className="text-2xl font-bold text-red-400">{r.errors_count}</div>
            <div className="text-xs text-slate-400">ERROR</div>
          </div>
          <div className="bg-amber-500/20 rounded-lg py-2">
            <div className="text-2xl font-bold text-amber-400">{r.warnings_count}</div>
            <div className="text-xs text-slate-400">WARN</div>
          </div>
          <div className="bg-blue-500/20 rounded-lg py-2">
            <div className="text-2xl font-bold text-blue-400">{r.info_count}</div>
            <div className="text-xs text-slate-400">INFO</div>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          {response.pdfUrl && (
            <a
              href={response.pdfUrl}
              download={response.pdfName || 'checked.pdf'}
              className="flex-1 text-center px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm"
            >
              📥 注釈PDFを保存
            </a>
          )}
          <button
            onClick={onReset}
            className="px-3 py-2 rounded-lg bg-dark-surface border border-dark-border hover:bg-dark-hover text-sm"
          >
            ← 別の図面
          </button>
        </div>
      </div>

      {/* 指摘一覧 */}
      <div className="rounded-xl bg-dark-surface border border-dark-border">
        <div className="px-4 py-3 border-b border-dark-border text-sm font-medium">
          指摘一覧 ({r.findings.length})
        </div>
        <div className="max-h-[calc(100vh-22rem)] overflow-y-auto">
          {r.findings.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              指摘事項はありません 🎉
            </div>
          ) : (
            <ul className="divide-y divide-dark-border">
              {r.findings.map((f, i) => (
                <FindingRow
                  key={i}
                  finding={f}
                  index={i}
                  selected={selectedIndex === i}
                  onSelect={() => onSelectFinding(selectedIndex === i ? null : i)}
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function FindingRow({
  finding,
  index,
  selected,
  onSelect,
}: {
  finding: Finding;
  index: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const meta = SEVERITY_META[finding.severity];
  return (
    <li
      onClick={onSelect}
      className={`
        px-4 py-3 cursor-pointer transition
        ${selected ? 'bg-dark-hover' : 'hover:bg-dark-hover/50'}
      `}
    >
      <div className="flex items-start gap-2">
        <div className={`shrink-0 text-xs font-bold px-1.5 py-0.5 rounded ${meta.bg} ${meta.text}`}>
          {meta.label}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm leading-relaxed">
            <span className="text-slate-500 mr-1">#{index + 1}</span>
            {finding.message}
          </div>
          {finding.suggestion && (
            <div className="mt-1 text-xs text-slate-400">→ {finding.suggestion}</div>
          )}
          <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
            <span>{finding.checker}</span>
            <span>·</span>
            <span>{finding.rule_id}</span>
            {finding.jis_reference && (
              <>
                <span>·</span>
                <span className="text-accent">{finding.jis_reference}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </li>
  );
}
