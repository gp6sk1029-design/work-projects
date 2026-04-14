import { Router } from 'express';
import { getDb, saveDb } from '../db/sqlite';
import fs from 'fs';

const router = Router();

// 履歴一覧
router.get('/', async (_req, res) => {
  try {
    const db = await getDb();
    const results = db.exec(`
      SELECT r.id, r.file_name, r.duration_seconds, r.audio_mode, r.is_video, r.created_at,
        CASE WHEN t.id IS NOT NULL THEN 1 ELSE 0 END as has_transcription
      FROM recordings r
      LEFT JOIN transcriptions t ON t.recording_id = r.id
      ORDER BY r.created_at DESC
      LIMIT 100
    `);

    if (results.length === 0) {
      res.json([]);
      return;
    }

    const items = results[0].values.map((row: any[]) => ({
      id: row[0],
      file_name: row[1],
      duration_seconds: row[2],
      audio_mode: row[3],
      is_video: row[4] === 1,
      created_at: row[5],
      has_transcription: row[6] === 1,
    }));

    res.json(items);
  } catch (err: any) {
    res.status(500).json({ error: '履歴取得エラー' });
  }
});

// 録音詳細（全関連データ）
router.get('/:id', async (req, res) => {
  try {
    const db = await getDb();
    const { id } = req.params;

    // 録音
    const recResult = db.exec('SELECT * FROM recordings WHERE id = ?', [id]);
    if (recResult.length === 0 || recResult[0].values.length === 0) {
      res.status(404).json({ error: '見つかりません' });
      return;
    }
    const r = recResult[0].values[0];
    const recording = {
      id: r[0], file_name: r[1], file_path: r[2], file_size: r[3],
      mime_type: r[4], duration_seconds: r[5], audio_mode: r[6],
      audio_analysis: r[7], is_video: r[8] === 1, created_at: r[9], updated_at: r[10],
    };

    // 文字起こし
    const transResult = db.exec('SELECT * FROM transcriptions WHERE recording_id = ?', [id]);
    let transcription = null;
    if (transResult.length > 0 && transResult[0].values.length > 0) {
      const t = transResult[0].values[0];
      transcription = {
        id: t[0], recording_id: t[1], full_text: t[2],
        segments: JSON.parse(t[3] as string), language: t[4], created_at: t[5],
      };
    }

    // 要約
    const sumResult = db.exec('SELECT * FROM summaries WHERE recording_id = ?', [id]);
    const summaries = sumResult.length > 0
      ? sumResult[0].values.map((s: any[]) => ({
          id: s[0], recording_id: s[1], summary_type: s[2], content: s[3], created_at: s[4],
        }))
      : [];

    // セクション
    const secResult = db.exec('SELECT * FROM sections WHERE recording_id = ? ORDER BY section_index', [id]);
    const sections = secResult.length > 0
      ? secResult[0].values.map((s: any[]) => ({
          id: s[0], recording_id: s[1], section_index: s[2], title: s[3],
          start_time: s[4], end_time: s[5], transcript_text: s[6],
          summary: s[7], mindmap_mermaid: s[8], user_comment: s[9], created_at: s[10],
        }))
      : [];

    // チャット
    const chatResult = db.exec('SELECT * FROM chat_messages WHERE recording_id = ? ORDER BY created_at', [id]);
    const chatMessages = chatResult.length > 0
      ? chatResult[0].values.map((c: any[]) => ({
          id: c[0], recording_id: c[1], role: c[2], content: c[3], created_at: c[4],
        }))
      : [];

    // マインドマップ
    const mmResult = db.exec('SELECT * FROM mindmaps WHERE recording_id = ?', [id]);
    const mindmaps = mmResult.length > 0
      ? mmResult[0].values.map((m: any[]) => ({
          id: m[0], recording_id: m[1], section_id: m[2], mermaid_code: m[3], created_at: m[4],
        }))
      : [];

    res.json({ recording, transcription, summaries, sections, chatMessages, mindmaps });
  } catch (err: any) {
    res.status(500).json({ error: '詳細取得エラー' });
  }
});

// 録音削除
router.delete('/:id', async (req, res) => {
  try {
    const db = await getDb();
    const { id } = req.params;

    // ファイル削除（元ファイル + 音声抽出ファイル）
    const recResult = db.exec('SELECT file_path, file_name FROM recordings WHERE id = ?', [id]);
    if (recResult.length > 0 && recResult[0].values.length > 0) {
      const filePath = recResult[0].values[0][0] as string;
      const fileName = recResult[0].values[0][1] as string;

      // 元ファイル削除
      if (filePath) {
        try { fs.unlinkSync(filePath); } catch {}
      }

      // 音声抽出ファイル（_audio.mp3）も削除
      if (filePath) {
        const audioPath = filePath.replace(/\.\w+$/, '_audio.mp3');
        try { fs.unlinkSync(audioPath); } catch {}
      }

      console.log(`削除完了: ${fileName} (ファイル + 全関連データ)`);
    }

    // DB削除（CASCADE）
    db.run('DELETE FROM chat_messages WHERE recording_id = ?', [id]);
    db.run('DELETE FROM mindmaps WHERE recording_id = ?', [id]);
    db.run('DELETE FROM sections WHERE recording_id = ?', [id]);
    db.run('DELETE FROM summaries WHERE recording_id = ?', [id]);
    db.run('DELETE FROM transcriptions WHERE recording_id = ?', [id]);
    db.run('DELETE FROM recordings WHERE id = ?', [id]);
    saveDb();

    res.json({ success: true });
  } catch (err: any) {
    res.status(500).json({ error: '削除エラー' });
  }
});

export default router;
