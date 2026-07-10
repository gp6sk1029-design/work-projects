import type { DiffResult, DiffStatus, DeviceCategory } from '../types';

interface Props {
  diff: DiffResult;
}

const STATUS_LABELS: Record<DiffStatus, { label: string; color: string; emoji: string }> = {
  changed: { label: 'コメント変更', color: 'text-diff-change', emoji: '🟡' },
  added: { label: 'Bで追加', color: 'text-diff-add', emoji: '🟢' },
  removed: { label: 'Aから削除', color: 'text-diff-remove', emoji: '🔴' },
  same: { label: '同一', color: 'text-diff-same', emoji: '⚪' },
};

const CATEGORY_LABELS: Record<DeviceCategory, string> = {
  X: 'X 物理入力', Y: 'Y 物理出力', R: 'R 内部リレー', L: 'L リンクリレー',
  T: 'T タイマー', C: 'C カウンタ', DT: 'DT データレジスタ', LD: 'LD リンクD',
  SD: 'SD システムD', SR: 'SR システムR', FL: 'FL ファイルレジスタ', P: 'P ポインタ',
  WX: 'WX ワード入力', WY: 'WY ワード出力', WR: 'WR ワードリレー', OTHER: 'その他',
};

export default function DiffSummary({ diff }: Props) {
  const { summary, metadata } = diff;
  const activeCategories = (Object.keys(summary.byCategory) as DeviceCategory[])
    .filter((cat) => {
      const v = summary.byCategory[cat];
      return v.added + v.removed + v.changed > 0;
    });

  return (
    <div className="space-y-4">
      {/* メタデータ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <div className="p-3 bg-dark-surface rounded border border-dark-border">
          <span className="text-xs text-gray-500">プロジェクト A</span>
          <p className="text-white font-mono break-all">{metadata.projectAName}</p>
          <p className="text-xs text-gray-400 mt-1">{metadata.countA} デバイス</p>
        </div>
        <div className="p-3 bg-dark-surface rounded border border-dark-border">
          <span className="text-xs text-gray-500">プロジェクト B</span>
          <p className="text-white font-mono break-all">{metadata.projectBName}</p>
          <p className="text-xs text-gray-400 mt-1">{metadata.countB} デバイス</p>
        </div>
      </div>

      {/* 状態別集計 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(['changed', 'added', 'removed', 'same'] as DiffStatus[]).map((s) => {
          const info = STATUS_LABELS[s];
          return (
            <div key={s} className="p-3 bg-dark-surface rounded border border-dark-border">
              <div className="text-xs text-gray-400 mb-1">
                {info.emoji} {info.label}
              </div>
              <div className={`text-2xl font-bold ${info.color}`}>
                {summary.byStatus[s]}
              </div>
            </div>
          );
        })}
      </div>

      {/* カテゴリ別集計（変更があるもののみ） */}
      {activeCategories.length > 0 && (
        <div className="p-4 bg-dark-surface rounded border border-dark-border">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">カテゴリ別の変更件数</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-400 border-b border-dark-border">
                <tr>
                  <th className="text-left py-1.5 px-2">カテゴリ</th>
                  <th className="text-center py-1.5 px-2 text-diff-change">変更</th>
                  <th className="text-center py-1.5 px-2 text-diff-add">追加</th>
                  <th className="text-center py-1.5 px-2 text-diff-remove">削除</th>
                </tr>
              </thead>
              <tbody>
                {activeCategories.map((cat) => {
                  const v = summary.byCategory[cat];
                  return (
                    <tr key={cat} className="border-b border-dark-border/30">
                      <td className="py-1.5 px-2 text-gray-300">{CATEGORY_LABELS[cat]}</td>
                      <td className="text-center py-1.5 px-2 text-diff-change">{v.changed || ''}</td>
                      <td className="text-center py-1.5 px-2 text-diff-add">{v.added || ''}</td>
                      <td className="text-center py-1.5 px-2 text-diff-remove">{v.removed || ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
