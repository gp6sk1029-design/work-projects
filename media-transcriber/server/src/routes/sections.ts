import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { getDb, saveDb } from '../db/sqlite';
import { detectSilence } from '../services/ffmpegService';
import { suggestSections, generateMindmap } from '../services/geminiService';
import { getModeParams } from '../services/audioAnalyzer';
import type { AudioMode } from '../types';

const router = Router();

// セクション分割実行
router.post('/', async (req, res) => {
  try {
    const { recordingId } = req.body;

    if (!recordingId) {
      res.status(400).json({ error: 'recordingIdが必要です' });
      return;
    }

    const db = await getDb();

    // 既存セクションチェック
    const existing = db.exec(
      'SELECT * FROM sections WHERE recording_id = ? ORDER BY section_index',
      [recordingId],
    );
    if (existing.length > 0 && existing[0].values.length > 0) {
      const sections = existing[0].values.map((row: any[]) => ({
        id: row[0],
        recording_id: row[1],
        section_index: row[2],
        title: row[3],
        start_time: row[4],
        end_time: row[5],
        transcript_text: row[6],
        summary: row[7],
        mindmap_mermaid: row[8],
        user_comment: row[9],
        created_at: row[10],
      }));
      res.json(sections);
      return;
    }

    // 録音情報取得
    const recording = db.exec('SELECT * FROM recordings WHERE id = ?', [recordingId]);
    if (recording.length === 0 || recording[0].values.length === 0) {
      res.status(404).json({ error: '録音が見つかりません' });
      return;
    }

    const recRow = recording[0].values[0];
    const filePath = recRow[2] as string;
    const duration = recRow[5] as number;
    const audioMode = recRow[6] as AudioMode;

    // 文字起こし取得
    const transcription = db.exec(
      'SELECT full_text, segments FROM transcriptions WHERE recording_id = ?',
      [recordingId],
    );
    if (transcription.length === 0 || transcription[0].values.length === 0) {
      res.status(404).json({ error: '文字起こしが見つかりません' });
      return;
    }

    const fullText = transcription[0].values[0][0] as string;
    const segments = JSON.parse(transcription[0].values[0][1] as string);

    // Stage 1: FFmpegで無音区間検出
    const modeParams = getModeParams(audioMode);
    const silences = await detectSilence(filePath, modeParams.silenceThresholdDb, modeParams.silenceMinDuration);

    // Stage 2: Geminiで意味的セクション分割
    const suggested = await suggestSections(fullText, silences, duration);

    // 各セクションの文字起こしテキスト抽出とマインドマップ生成
    const now = new Date().toISOString();
    const savedSections = [];

    for (let i = 0; i < suggested.length; i++) {
      const sec = suggested[i];

      // セクション内のセグメントからテキスト抽出
      const sectionSegments = segments.filter(
        (seg: any) => seg.start >= sec.start_time && seg.start < sec.end_time,
      );
      const sectionText = sectionSegments.map((s: any) => s.text).join('\n') || sec.summary;

      // セクション用マインドマップ生成
      let mindmapCode = '';
      try {
        mindmapCode = await generateMindmap(sectionText, sec.title);
      } catch { /* マインドマップ生成失敗は無視 */ }

      const id = uuidv4();
      db.run(
        `INSERT INTO sections (id, recording_id, section_index, title, start_time, end_time, transcript_text, summary, mindmap_mermaid, user_comment, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [id, recordingId, i, sec.title, sec.start_time, sec.end_time, sectionText, sec.summary, mindmapCode, '', now],
      );

      savedSections.push({
        id,
        recording_id: recordingId,
        section_index: i,
        title: sec.title,
        start_time: sec.start_time,
        end_time: sec.end_time,
        transcript_text: sectionText,
        summary: sec.summary,
        mindmap_mermaid: mindmapCode,
        user_comment: '',
        created_at: now,
      });
    }

    saveDb();
    res.json(savedSections);
  } catch (err: any) {
    console.error('セクション分割エラー:', err);
    res.status(500).json({ error: err.message || 'セクション分割に失敗しました' });
  }
});

// セクションコメント更新
router.patch('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { comment } = req.body;

    const db = await getDb();
    db.run('UPDATE sections SET user_comment = ? WHERE id = ?', [comment || '', id]);
    saveDb();

    res.json({ success: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
