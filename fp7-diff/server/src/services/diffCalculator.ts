/**
 * グローバルデバイスの差分計算
 *  - 「アドレス」をJOINキーとして両プロジェクトをマッチング
 *  - 4状態に分類：added / removed / changed / same
 *  - カテゴリ別集計（X/Y/R/DT/SD等）も併せて出力
 */
import type { DeviceEntry, DeviceCategory } from './globalDeviceParser';

export type DiffStatus = 'added' | 'removed' | 'changed' | 'same';

export interface DiffRow {
  address: string;
  category: DeviceCategory;
  status: DiffStatus;
  commentA: string;     // プロジェクトA側のコメント
  commentB: string;     // プロジェクトB側のコメント
}

export interface DiffSummary {
  total: number;
  byStatus: Record<DiffStatus, number>;
  byCategory: Record<DeviceCategory, Record<DiffStatus, number>>;
}

export interface DiffResult {
  rows: DiffRow[];
  summary: DiffSummary;
  metadata: {
    projectAName: string;
    projectBName: string;
    countA: number;
    countB: number;
    generatedAt: string;
  };
}

const EMPTY_STATUS: Record<DiffStatus, number> = {
  added: 0,
  removed: 0,
  changed: 0,
  same: 0,
};

const ALL_CATEGORIES: DeviceCategory[] = [
  'X', 'Y', 'R', 'L', 'T', 'C', 'DT', 'LD', 'SD', 'SR', 'FL', 'P', 'WX', 'WY', 'WR', 'OTHER',
];

export function calculateDiff(
  entriesA: DeviceEntry[],
  entriesB: DeviceEntry[],
  projectAName: string,
  projectBName: string,
): DiffResult {
  const mapA = new Map(entriesA.map((e) => [e.address, e]));
  const mapB = new Map(entriesB.map((e) => [e.address, e]));

  const rows: DiffRow[] = [];

  // 全アドレスのユニオン
  const allAddrs = new Set([...mapA.keys(), ...mapB.keys()]);
  for (const addr of allAddrs) {
    const a = mapA.get(addr);
    const b = mapB.get(addr);
    let status: DiffStatus;
    if (a && b) {
      status = a.comment === b.comment ? 'same' : 'changed';
    } else if (a) {
      status = 'removed';
    } else {
      status = 'added';
    }
    rows.push({
      address: addr,
      category: (a || b)!.category,
      status,
      commentA: a?.comment || '',
      commentB: b?.comment || '',
    });
  }

  // ソート: changed > added > removed > same の順、その中はアドレス順
  const statusOrder: Record<DiffStatus, number> = { changed: 0, added: 1, removed: 2, same: 3 };
  rows.sort((x, y) => {
    const so = statusOrder[x.status] - statusOrder[y.status];
    if (so !== 0) return so;
    return x.address.localeCompare(y.address);
  });

  // サマリ集計
  const byStatus = { ...EMPTY_STATUS };
  const byCategory = {} as Record<DeviceCategory, Record<DiffStatus, number>>;
  for (const cat of ALL_CATEGORIES) {
    byCategory[cat] = { ...EMPTY_STATUS };
  }
  for (const r of rows) {
    byStatus[r.status]++;
    byCategory[r.category][r.status]++;
  }

  return {
    rows,
    summary: {
      total: rows.length,
      byStatus,
      byCategory,
    },
    metadata: {
      projectAName,
      projectBName,
      countA: entriesA.length,
      countB: entriesB.length,
      generatedAt: new Date().toISOString(),
    },
  };
}
