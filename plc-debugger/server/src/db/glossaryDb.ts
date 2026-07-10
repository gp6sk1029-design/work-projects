/**
 * 設備翻訳：略語辞書DB（社内用語の蓄積）
 * 既存の sqlite.ts と同じDBインスタンスを共有（sql.js）
 */
import { getDb, saveDb } from './sqlite';

export interface GlossaryEntry {
  id: number;
  term_ja: string;
  term_en: string;
  abbr: string;
  category: string;        // "電気" | "機械" | "制御" | "安全" | "その他"
  note: string;
  hit_count: number;
  created_at: string;
  updated_at: string;
}

/** テーブル初期化（idempotent） */
export async function initGlossaryTable(): Promise<void> {
  const db = await getDb();
  db.run(`
    CREATE TABLE IF NOT EXISTS glossary (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      term_ja TEXT NOT NULL,
      term_en TEXT NOT NULL,
      abbr TEXT NOT NULL DEFAULT '',
      category TEXT DEFAULT 'その他',
      note TEXT DEFAULT '',
      hit_count INTEGER DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(term_ja, term_en, abbr)
    )
  `);
  saveDb();
}

/** 用語の追加 or 更新（重複時はhit_count++） */
export async function upsertGlossary(
  entry: Omit<GlossaryEntry, 'id' | 'hit_count' | 'created_at' | 'updated_at'>,
): Promise<void> {
  const db = await getDb();
  const now = new Date().toISOString();

  // 既存チェック
  const res = db.exec(
    'SELECT id FROM glossary WHERE term_ja = ? AND term_en = ? AND abbr = ?',
    [entry.term_ja, entry.term_en, entry.abbr || ''],
  );

  if (res.length > 0 && res[0].values.length > 0) {
    const id = res[0].values[0][0];
    db.run(
      'UPDATE glossary SET hit_count = hit_count + 1, updated_at = ?, note = ?, category = ? WHERE id = ?',
      [now, entry.note || '', entry.category || 'その他', id as number],
    );
  } else {
    db.run(
      `INSERT INTO glossary (term_ja, term_en, abbr, category, note, hit_count, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, 1, ?, ?)`,
      [
        entry.term_ja,
        entry.term_en,
        entry.abbr || '',
        entry.category || 'その他',
        entry.note || '',
        now,
        now,
      ],
    );
  }
  saveDb();
}

/** 全件取得（hit_count降順） */
export async function listGlossary(): Promise<GlossaryEntry[]> {
  const db = await getDb();
  const res = db.exec(
    'SELECT id, term_ja, term_en, abbr, category, note, hit_count, created_at, updated_at FROM glossary ORDER BY hit_count DESC, updated_at DESC',
  );
  if (res.length === 0) return [];
  return res[0].values.map((row: any[]) => ({
    id: row[0] as number,
    term_ja: row[1] as string,
    term_en: row[2] as string,
    abbr: row[3] as string,
    category: row[4] as string,
    note: row[5] as string,
    hit_count: row[6] as number,
    created_at: row[7] as string,
    updated_at: row[8] as string,
  }));
}

/** 検索（term_ja / term_en / abbr のいずれかに部分一致） */
export async function searchGlossary(query: string): Promise<GlossaryEntry[]> {
  const db = await getDb();
  const q = `%${query}%`;
  const res = db.exec(
    `SELECT id, term_ja, term_en, abbr, category, note, hit_count, created_at, updated_at
     FROM glossary
     WHERE term_ja LIKE ? OR term_en LIKE ? OR abbr LIKE ?
     ORDER BY hit_count DESC LIMIT 20`,
    [q, q, q],
  );
  if (res.length === 0) return [];
  return res[0].values.map((row: any[]) => ({
    id: row[0] as number,
    term_ja: row[1] as string,
    term_en: row[2] as string,
    abbr: row[3] as string,
    category: row[4] as string,
    note: row[5] as string,
    hit_count: row[6] as number,
    created_at: row[7] as string,
    updated_at: row[8] as string,
  }));
}

/** 削除 */
export async function deleteGlossary(id: number): Promise<void> {
  const db = await getDb();
  db.run('DELETE FROM glossary WHERE id = ?', [id]);
  saveDb();
}

/** ヒットカウント+1（既存エントリの再利用通知） */
export async function bumpHitCount(id: number): Promise<void> {
  const db = await getDb();
  db.run('UPDATE glossary SET hit_count = hit_count + 1, updated_at = ? WHERE id = ?', [
    new Date().toISOString(),
    id,
  ]);
  saveDb();
}
