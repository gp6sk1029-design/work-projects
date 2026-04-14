import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import zlib from 'zlib';
import { promisify } from 'util';
import { v4 as uuidv4 } from 'uuid';
import { getDb, saveDb } from '../db/sqlite';

const gunzip = promisify(zlib.gunzip);

const storage = multer.diskStorage({
  destination: path.join(process.cwd(), 'uploads'),
  filename: (_req, file, cb) => cb(null, `import_${Date.now()}_${file.originalname}`),
});
const upload = multer({ storage, limits: { fileSize: 50 * 1024 * 1024 } }); // 50MB上限

const router = Router();

// .mt.json.gz ファイルをインポート
router.post('/', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      res.status(400).json({ error: 'ファイルが見つかりません' });
      return;
    }

    const filePath = req.file.path;
    const rawData = fs.readFileSync(filePath);

    let jsonStr: string;
    // .gz なら解凍、そうでなければそのまま
    if (req.file.originalname.endsWith('.gz')) {
      const decompressed = await gunzip(rawData);
      jsonStr = decompressed.toString('utf-8');
    } else {
      jsonStr = rawData.toString('utf-8');
    }

    const data = JSON.parse(jsonStr);

    if (!data.version || !data.recording) {
      res.status(400).json({ error: '無効なMedia Transcriberファイルです' });
      return;
    }

    const db = await getDb();
    const now = new Date().toISOString();

    // 録音レコード作成
    const recordingId = uuidv4();
    db.run(
      `INSERT INTO recordings (id, file_name, file_path, file_size, mime_type, duration_seconds, audio_mode, audio_analysis, is_video, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        recordingId,
        data.recording.file_name || 'imported',
        '',  // ファイルパスなし（インポートデータ）
        0,
        data.recording.mime_type || 'audio/mpeg',
        data.recording.duration_seconds || 0,
        data.recording.audio_mode || 'unknown',
        '{}',
        data.recording.is_video ? 1 : 0,
        data.recording.created_at || now,
        now,
      ],
    );

    // 文字起こし
    if (data.transcription) {
      db.run(
        `INSERT INTO transcriptions (id, recording_id, full_text, segments, language, created_at) VALUES (?, ?, ?, ?, ?, ?)`,
        [uuidv4(), recordingId, data.transcription.full_text, JSON.stringify(data.transcription.segments || []), data.transcription.language || 'ja', now],
      );
    }

    // 要約
    for (const s of (data.summaries || [])) {
      db.run(
        'INSERT INTO summaries (id, recording_id, summary_type, content, created_at) VALUES (?, ?, ?, ?, ?)',
        [uuidv4(), recordingId, s.summary_type, s.content, now],
      );
    }

    // セクション
    for (const s of (data.sections || [])) {
      db.run(
        `INSERT INTO sections (id, recording_id, section_index, title, start_time, end_time, transcript_text, summary, mindmap_mermaid, user_comment, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [uuidv4(), recordingId, s.section_index, s.title, s.start_time, s.end_time, s.transcript_text || '', s.summary || '', s.mindmap_mermaid || '', s.user_comment || '', now],
      );
    }

    // チャット
    for (const c of (data.chatMessages || [])) {
      db.run(
        'INSERT INTO chat_messages (id, recording_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)',
        [uuidv4(), recordingId, c.role, c.content, c.created_at || now],
      );
    }

    // マインドマップ
    for (const m of (data.mindmaps || [])) {
      db.run(
        'INSERT INTO mindmaps (id, recording_id, section_id, mermaid_code, created_at) VALUES (?, ?, ?, ?, ?)',
        [uuidv4(), recordingId, null, m.mermaid_code, now],
      );
    }

    saveDb();

    // 一時ファイル削除
    try { fs.unlinkSync(filePath); } catch {}

    res.json({ recordingId, message: 'インポート完了' });
  } catch (err: any) {
    console.error('インポートエラー:', err);
    res.status(500).json({ error: err.message || 'インポートに失敗しました' });
  }
});

export default router;
