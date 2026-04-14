import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb, saveDb } from '../db/sqlite';
import { chat } from '../services/geminiService';

const router = Router();

router.post('/', async (req, res) => {
  try {
    const { recordingId, message, history } = req.body as {
      recordingId: string;
      message: string;
      history?: { role: 'user' | 'assistant'; content: string }[];
    };

    if (!recordingId || !message) {
      res.status(400).json({ error: 'recordingIdとmessageが必要です' });
      return;
    }

    const db = await getDb();

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

    // Gemini用の履歴形式に変換
    const geminiHistory = (history || []).map((msg) => ({
      role: msg.role === 'assistant' ? 'model' as const : 'user' as const,
      parts: [{ text: msg.content }],
    }));

    // チャット実行
    const reply = await chat(message, fullText, geminiHistory);

    // ユーザーメッセージ保存
    const userMsgId = uuidv4();
    const now = new Date().toISOString();
    db.run(
      'INSERT INTO chat_messages (id, recording_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)',
      [userMsgId, recordingId, 'user', message, now],
    );

    // アシスタントメッセージ保存
    const assistantMsgId = uuidv4();
    db.run(
      'INSERT INTO chat_messages (id, recording_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)',
      [assistantMsgId, recordingId, 'assistant', reply, new Date().toISOString()],
    );
    saveDb();

    res.json({
      id: assistantMsgId,
      recording_id: recordingId,
      role: 'assistant',
      content: reply,
      created_at: new Date().toISOString(),
    });
  } catch (err: any) {
    console.error('チャットエラー:', err);
    res.status(500).json({ error: err.message || 'チャット処理に失敗しました' });
  }
});

export default router;
