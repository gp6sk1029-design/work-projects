import initSqlJs, { Database } from 'sql.js';
import path from 'path';
import fs from 'fs';

let db: Database | null = null;
const DB_PATH = path.join(process.cwd(), 'data', 'media-transcriber.db');

export async function getDb(): Promise<Database> {
  if (db) return db;

  const SQL = await initSqlJs();

  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  if (fs.existsSync(DB_PATH)) {
    const buffer = fs.readFileSync(DB_PATH);
    db = new SQL.Database(buffer);
  } else {
    db = new SQL.Database();
  }

  // テーブル作成
  db.run(`
    CREATE TABLE IF NOT EXISTS recordings (
      id TEXT PRIMARY KEY,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      file_size INTEGER NOT NULL,
      mime_type TEXT NOT NULL,
      duration_seconds REAL DEFAULT 0,
      audio_mode TEXT DEFAULT 'unknown',
      audio_analysis TEXT DEFAULT '{}',
      is_video INTEGER DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS transcriptions (
      id TEXT PRIMARY KEY,
      recording_id TEXT NOT NULL,
      full_text TEXT NOT NULL,
      segments TEXT DEFAULT '[]',
      language TEXT DEFAULT 'ja',
      created_at TEXT NOT NULL,
      FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS summaries (
      id TEXT PRIMARY KEY,
      recording_id TEXT NOT NULL,
      summary_type TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS sections (
      id TEXT PRIMARY KEY,
      recording_id TEXT NOT NULL,
      section_index INTEGER NOT NULL,
      title TEXT NOT NULL,
      start_time REAL NOT NULL,
      end_time REAL NOT NULL,
      transcript_text TEXT DEFAULT '',
      summary TEXT DEFAULT '',
      mindmap_mermaid TEXT DEFAULT '',
      user_comment TEXT DEFAULT '',
      created_at TEXT NOT NULL,
      FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS chat_messages (
      id TEXT PRIMARY KEY,
      recording_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS mindmaps (
      id TEXT PRIMARY KEY,
      recording_id TEXT NOT NULL,
      section_id TEXT,
      mermaid_code TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
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
