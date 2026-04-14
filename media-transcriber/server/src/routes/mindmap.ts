import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb, saveDb } from '../db/sqlite';
import { generateMindmap } from '../services/geminiService';

const router = Router();

router.post('/', async (req, res) => {
  try {
    const { recordingId, sectionId } = req.body as { recordingId: string; sectionId?: string };

    if (!recordingId) {
      res.status(400).json({ error: 'recordingIdが必要です' });
      return;
    }

    const db = await getDb();

    // 既存のマインドマップをチェック
    const existing = db.exec(
      'SELECT * FROM mindmaps WHERE recording_id = ? AND section_id IS ?',
      [recordingId, sectionId || null],
    );
    if (existing.length > 0 && existing[0].values.length > 0) {
      const row = existing[0].values[0];
      res.json({
        id: row[0],
        recording_id: row[1],
        section_id: row[2],
        mermaid_code: row[3],
        created_at: row[4],
      });
      return;
    }

    let text = '';
    let title = '';

    if (sectionId) {
      // セクション指定の場合
      const section = db.exec(
        'SELECT title, transcript_text FROM sections WHERE id = ?',
        [sectionId],
      );
      if (section.length > 0 && section[0].values.length > 0) {
        title = section[0].values[0][0] as string;
        text = section[0].values[0][1] as string;
      }
    } else {
      // 全体
      const transcription = db.exec(
        'SELECT full_text FROM transcriptions WHERE recording_id = ?',
        [recordingId],
      );
      if (transcription.length > 0 && transcription[0].values.length > 0) {
        text = transcription[0].values[0][0] as string;
        title = '全体の構造';
      }
    }

    if (!text) {
      res.status(404).json({ error: 'テキストが見つかりません' });
      return;
    }

    const mermaidCode = await generateMindmap(text, title);

    const id = uuidv4();
    const now = new Date().toISOString();

    db.run(
      'INSERT INTO mindmaps (id, recording_id, section_id, mermaid_code, created_at) VALUES (?, ?, ?, ?, ?)',
      [id, recordingId, sectionId || null, mermaidCode, now],
    );
    saveDb();

    res.json({
      id,
      recording_id: recordingId,
      section_id: sectionId || null,
      mermaid_code: mermaidCode,
      created_at: now,
    });
  } catch (err: any) {
    console.error('マインドマップエラー:', err);
    res.status(500).json({ error: err.message || 'マインドマップ生成に失敗しました' });
  }
});

export default router;
