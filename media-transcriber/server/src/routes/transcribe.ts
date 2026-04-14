import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb, saveDb } from '../db/sqlite';
import { processFileForGemini } from '../services/fileProcessor';
import { transcribe } from '../services/geminiService';
import type { AudioMode } from '../types';

const router = Router();

// 通常のPOSTエンドポイント（SSEではなく通常レスポンス）
router.post('/', async (req, res) => {
  // 長時間処理のためタイムアウトを10分に設定
  req.setTimeout(600000);
  res.setTimeout(600000);

  try {
    const { recordingId } = req.body;
    if (!recordingId) {
      res.status(400).json({ error: 'recordingIdが必要です' });
      return;
    }

    const db = await getDb();
    const results = db.exec('SELECT * FROM recordings WHERE id = ?', [recordingId]);
    if (results.length === 0 || results[0].values.length === 0) {
      res.status(404).json({ error: '録音が見つかりません' });
      return;
    }

    // 既に文字起こし済みならそれを返す
    const existing = db.exec('SELECT * FROM transcriptions WHERE recording_id = ?', [recordingId]);
    if (existing.length > 0 && existing[0].values.length > 0) {
      const t = existing[0].values[0];
      res.json({
        id: t[0],
        recording_id: t[1],
        full_text: t[2],
        segments: JSON.parse(t[3] as string),
        language: t[4],
        created_at: t[5],
      });
      return;
    }

    const row = results[0].values[0];
    const filePath = row[2] as string;
    const mimeType = row[4] as string;
    const audioMode = row[6] as AudioMode;
    const isVideo = (row[8] as number) === 1;

    console.log(`文字起こし開始: ${filePath} (mode: ${audioMode}, video: ${isVideo})`);

    // Step 1: Gemini File APIにアップロード
    const processed = await processFileForGemini(filePath, mimeType, (msg) => {
      console.log(`  進捗: ${msg}`);
    });

    console.log(`  アップロード完了, chunked: ${processed.isChunked}`);

    // Step 2: 文字起こし実行
    let fullText = '';
    let segments: any[] = [];

    if (processed.isChunked && processed.chunks) {
      for (let i = 0; i < processed.chunks.length; i++) {
        const chunk = processed.chunks[i];
        console.log(`  チャンク ${i + 1}/${processed.chunks.length} を文字起こし中...`);

        const result = await transcribe(chunk.fileUri, chunk.mimeType, audioMode, isVideo);
        fullText += (fullText ? '\n' : '') + result.fullText;

        const offsetSegments = result.segments.map((seg) => ({
          ...seg,
          start: seg.start + chunk.offsetSeconds,
          end: seg.end + chunk.offsetSeconds,
        }));
        segments.push(...offsetSegments);
      }
    } else {
      console.log('  Gemini文字起こし実行中（数分かかる場合があります）...');
      const result = await transcribe(processed.fileUri, mimeType, audioMode, isVideo);
      fullText = result.fullText;
      segments = result.segments;
    }

    console.log(`  文字起こし完了: ${fullText.length}文字`);

    // DB保存
    const transcriptionId = uuidv4();
    db.run(
      `INSERT INTO transcriptions (id, recording_id, full_text, segments, language, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [transcriptionId, recordingId, fullText, JSON.stringify(segments), 'ja', new Date().toISOString()],
    );
    saveDb();

    res.json({
      id: transcriptionId,
      recording_id: recordingId,
      full_text: fullText,
      segments,
      language: 'ja',
      created_at: new Date().toISOString(),
    });
  } catch (err: any) {
    console.error('文字起こしエラー:', err);
    res.status(500).json({ error: err.message || '文字起こしに失敗しました' });
  }
});

export default router;
