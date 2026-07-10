/**
 * 比較履歴の保存・取得（sql.js）
 */
import initSqlJs from 'sql.js';
import path from 'path';
import fs from 'fs';

let db: any = null;
const DB_PATH = path.join(process.cwd(), 'data', 'fp7-diff.db');

export async function getDb(): Promise<any> {
  if (db) return db;
  const SQL = await initSqlJs();
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  if (fs.existsSync(DB_PATH)) {
    const buffer = fs.readFileSync(DB_PATH);
    db = new SQL.Database(buffer);
  } else {
    db = new SQL.Database();
  }
  db.run(`
    CREATE TABLE IF NOT EXISTS compare_history (
      id TEXT PRIMARY KEY,
      project_a TEXT NOT NULL,
      project_b TEXT NOT NULL,
      created_at TEXT NOT NULL,
      diff_summary TEXT NOT NULL,
      diff_rows TEXT NOT NULL,
      ai_summary TEXT
    )
  `);
  saveDb();
  return db;
}

export function saveDb() {
  if (!db) return;
  const data = db.export();
  const buffer = Buffer.from(data);
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(DB_PATH, buffer);
}

export async function saveCompareHistory(
  id: string,
  projectA: string,
  projectB: string,
  diffSummary: any,
  diffRows: any,
  aiSummary: any,
): Promise<void> {
  const database = await getDb();
  database.run(
    `INSERT OR REPLACE INTO compare_history (id, project_a, project_b, created_at, diff_summary, diff_rows, ai_summary)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [
      id,
      projectA,
      projectB,
      new Date().toISOString(),
      JSON.stringify(diffSummary),
      JSON.stringify(diffRows),
      aiSummary ? JSON.stringify(aiSummary) : null,
    ],
  );
  saveDb();
}

export async function listCompareHistory(): Promise<any[]> {
  const database = await getDb();
  const res = database.exec(
    `SELECT id, project_a, project_b, created_at FROM compare_history ORDER BY created_at DESC LIMIT 50`,
  );
  if (res.length === 0) return [];
  return res[0].values.map((row: any[]) => ({
    id: row[0],
    projectA: row[1],
    projectB: row[2],
    createdAt: row[3],
  }));
}
