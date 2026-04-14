import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb, saveDb } from '../db/sqlite';
import { summarize } from '../services/geminiService';
import type { SummaryType } from '../types';

const router = Router();

router.post('/', async (req, res) => {
  try {
    const { recordingId, type } = req.body as { recordingId: string; type: SummaryType };

    if (!recordingId || !type) {
      res.status(400).json({ error: 'recordingIdとtypeが必要です' });
      return;
    }

    const validTypes: SummaryType[] = ['brief', 'detailed', 'minutes', 'action_items'];
    if (!validTypes.includes(type)) {
      res.status(400).json({ error: '無効な要約タイプです' });
      return;
    }

    const db = await getDb();

    // 既存の要約をチェック
    const existing = db.exec(
      'SELECT * FROM summaries WHERE recording_id = ? AND summary_type = ?',
      [recordingId, type],
    );
    if (existing.length > 0 && existing[0].values.length > 0) {
      const row = existing[0].values[0];
      res.json({
        id: row[0],
        recording_id: row[1],
        summary_type: row[2],
        content: row[3],
        created_at: row[4],
      });
      return;
    }

    // 文字起こしテキスト取得
    const transcription = db.exec(
      'SELECT full_text FROM transcriptions WHERE recording_id = ?',
      [recordingId],
    );
    if (transcription.length === 0 || transcription[0].values.length === 0) {
      res.status(404).json({ error: '文字起こしが見つかりません' });
      return;
    }

    const fullText = transcription[0].values[0][0] as string;

    // 要約生成
    const content = await summarize(fullText, type);

    const id = uuidv4();
    const now = new Date().toISOString();

    db.run(
      'INSERT INTO summaries (id, recording_id, summary_type, content, created_at) VALUES (?, ?, ?, ?, ?)',
      [id, recordingId, type, content, now],
    );
    saveDb();

    res.json({ id, recording_id: recordingId, summary_type: type, content, created_at: now });
  } catch (err: any) {
    console.error('要約エラー:', err);
    res.status(500).json({ error: err.message || '要約生成に失敗しました' });
  }
});

export default router;
