import initSqlJs, { Database } from 'sql.js';
import path from 'path';
import fs from 'fs';

let db: Database | null = null;
const DB_PATH = path.join(process.cwd(), 'data', 'plc-debugger.db');

export async function getDb(): Promise<Database> {
  if (db) return db;

  const SQL = await initSqlJs();

  // データディレクトリ作成
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  // 既存DBがあれば読み込む
  if (fs.existsSync(DB_PATH)) {
    const buffer = fs.readFileSync(DB_PATH);
    db = new SQL.Database(buffer);
  } else {
    db = new SQL.Database();
  }

  // テーブル作成
  db.run(`
    CREATE TABLE IF NOT EXISTS analysis_history (
      id TEXT PRIMARY KEY,
      project_name TEXT NOT NULL,
      created_at TEXT NOT NULL,
      project_data TEXT NOT NULL,
      analysis_result TEXT,
      file_names TEXT
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
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(DB_PATH, buffer);
}

export async function saveAnalysis(
  id: string,
  projectName: string,
  projectData: any,
  analysisResult: any,
  fileNames: string[],
) {
  const database = await getDb();
  database.run(
    `INSERT OR REPLACE INTO analysis_history (id, project_name, created_at, project_data, analysis_result, file_names)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [id, projectName, new Date().toISOString(), JSON.stringify(projectData), JSON.stringify(analysisResult), JSON.stringify(fileNames)],
  );
  saveDb();
}

export async function getAnalysisHistory(): Promise<any[]> {
  const database = await getDb();
  const results = database.exec(
    'SELECT id, project_name, created_at, file_names FROM analysis_history ORDER BY created_at DESC LIMIT 50',
  );

  if (results.length === 0) return [];

  return results[0].values.map((row: any[]) => ({
    id: row[0],
    projectName: row[1],
    createdAt: row[2],
    fileNames: JSON.parse(row[3] as string),
  }));
}

export async function getAnalysisById(id: string): Promise<any | null> {
  const database = await getDb();
  const results = database.exec(
    'SELECT * FROM analysis_history WHERE id = ?',
    [id],
  );

  if (results.length === 0 || results[0].values.length === 0) return null;

  const row = results[0].values[0];
  return {
    id: row[0],
    projectName: row[1],
    createdAt: row[2],
    projectData: JSON.parse(row[3] as string),
    analysisResult: row[4] ? JSON.parse(row[4] as string) : null,
    fileNames: JSON.parse(row[5] as string),
  };
}
