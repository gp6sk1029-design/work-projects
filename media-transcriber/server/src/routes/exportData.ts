import { Router } from 'express';
import { getDb } from '../db/sqlite';
import ExcelJS from 'exceljs';
import { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, BorderStyle } from 'docx';
import zlib from 'zlib';
import { promisify } from 'util';

const gzip = promisify(zlib.gzip);
const router = Router();

// 録音の全データを取得するヘルパー
async function getRecordingFullData(recordingId: string) {
  const db = await getDb();

  const recResult = db.exec('SELECT * FROM recordings WHERE id = ?', [recordingId]);
  if (recResult.length === 0 || recResult[0].values.length === 0) return null;

  const r = recResult[0].values[0];
  const recording = {
    id: r[0], file_name: r[1], file_path: r[2], file_size: r[3],
    mime_type: r[4], duration_seconds: r[5], audio_mode: r[6],
    audio_analysis: r[7], is_video: r[8] === 1, created_at: r[9], updated_at: r[10],
  };

  const transResult = db.exec('SELECT * FROM transcriptions WHERE recording_id = ?', [recordingId]);
  let transcription = null;
  if (transResult.length > 0 && transResult[0].values.length > 0) {
    const t = transResult[0].values[0];
    transcription = {
      id: t[0], recording_id: t[1], full_text: t[2],
      segments: JSON.parse(t[3] as string), language: t[4], created_at: t[5],
    };
  }

  const sumResult = db.exec('SELECT * FROM summaries WHERE recording_id = ?', [recordingId]);
  const summaries = sumResult.length > 0
    ? sumResult[0].values.map((s: any[]) => ({
        id: s[0], recording_id: s[1], summary_type: s[2], content: s[3], created_at: s[4],
      }))
    : [];

  const secResult = db.exec('SELECT * FROM sections WHERE recording_id = ? ORDER BY section_index', [recordingId]);
  const sections = secResult.length > 0
    ? secResult[0].values.map((s: any[]) => ({
        id: s[0], recording_id: s[1], section_index: s[2], title: s[3],
        start_time: s[4], end_time: s[5], transcript_text: s[6],
        summary: s[7], mindmap_mermaid: s[8], user_comment: s[9], created_at: s[10],
      }))
    : [];

  const chatResult = db.exec('SELECT * FROM chat_messages WHERE recording_id = ? ORDER BY created_at', [recordingId]);
  const chatMessages = chatResult.length > 0
    ? chatResult[0].values.map((c: any[]) => ({
        id: c[0], recording_id: c[1], role: c[2], content: c[3], created_at: c[4],
      }))
    : [];

  const mmResult = db.exec('SELECT * FROM mindmaps WHERE recording_id = ?', [recordingId]);
  const mindmaps = mmResult.length > 0
    ? mmResult[0].values.map((m: any[]) => ({
        id: m[0], recording_id: m[1], section_id: m[2], mermaid_code: m[3], created_at: m[4],
      }))
    : [];

  return { recording, transcription, summaries, sections, chatMessages, mindmaps };
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

const summaryTypeLabels: Record<string, string> = {
  brief: '簡潔要約',
  detailed: '詳細要約',
  minutes: '議事録',
  action_items: 'アクションアイテム',
};

// ===== Excel (.xlsx) エクスポート =====
router.get('/xlsx/:id', async (req, res) => {
  try {
    const data = await getRecordingFullData(req.params.id);
    if (!data) { res.status(404).json({ error: '見つかりません' }); return; }

    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'Media Transcriber';

    // シート1: 概要
    const infoSheet = workbook.addWorksheet('概要');
    infoSheet.columns = [{ width: 20 }, { width: 60 }];
    infoSheet.addRow(['ファイル名', data.recording.file_name]);
    infoSheet.addRow(['長さ', formatTime(data.recording.duration_seconds as number)]);
    infoSheet.addRow(['モード', data.recording.audio_mode === 'face_to_face' ? '対面録音' : data.recording.audio_mode === 'phone_call' ? '通話録音' : '自動']);
    infoSheet.addRow(['種類', data.recording.is_video ? '動画' : '音声']);
    infoSheet.addRow(['作成日', data.recording.created_at]);
    infoSheet.getRow(1).font = { bold: true };

    // シート2: 文字起こし
    if (data.transcription) {
      const transSheet = workbook.addWorksheet('文字起こし');
      transSheet.columns = [
        { header: '開始', width: 10 },
        { header: '終了', width: 10 },
        { header: '話者', width: 12 },
        { header: 'テキスト', width: 80 },
      ];
      transSheet.getRow(1).font = { bold: true };

      for (const seg of data.transcription.segments) {
        transSheet.addRow([
          formatTime(seg.start),
          formatTime(seg.end),
          seg.speaker || '',
          seg.text,
        ]);
      }
    }

    // シート3〜: 要約
    for (const summary of data.summaries) {
      const label = summaryTypeLabels[summary.summary_type] || summary.summary_type;
      const sheet = workbook.addWorksheet(label);
      sheet.columns = [{ width: 100 }];
      // 長文を改行で分割
      const lines = (summary.content as string).split('\n');
      for (const line of lines) {
        sheet.addRow([line]);
      }
    }

    // シート: セクション
    if (data.sections.length > 0) {
      const secSheet = workbook.addWorksheet('セクション');
      secSheet.columns = [
        { header: '#', width: 5 },
        { header: 'タイトル', width: 30 },
        { header: '開始', width: 10 },
        { header: '終了', width: 10 },
        { header: '要約', width: 50 },
        { header: 'コメント', width: 30 },
      ];
      secSheet.getRow(1).font = { bold: true };

      for (const sec of data.sections) {
        secSheet.addRow([
          (sec.section_index as number) + 1,
          sec.title,
          formatTime(sec.start_time as number),
          formatTime(sec.end_time as number),
          sec.summary,
          sec.user_comment,
        ]);
      }
    }

    // シート: Q&A
    if (data.chatMessages.length > 0) {
      const chatSheet = workbook.addWorksheet('Q&A');
      chatSheet.columns = [
        { header: '役割', width: 12 },
        { header: '内容', width: 80 },
        { header: '日時', width: 20 },
      ];
      chatSheet.getRow(1).font = { bold: true };

      for (const msg of data.chatMessages) {
        chatSheet.addRow([
          msg.role === 'user' ? '質問' : '回答',
          msg.content,
          msg.created_at,
        ]);
      }
    }

    const buffer = await workbook.xlsx.writeBuffer();
    const fileName = encodeURIComponent(data.recording.file_name?.toString().replace(/\.\w+$/, '') || 'export') + '.xlsx';

    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
    res.send(Buffer.from(buffer as ArrayBuffer));
  } catch (err: any) {
    console.error('Excelエクスポートエラー:', err);
    res.status(500).json({ error: err.message });
  }
});

// ===== Word (.docx) エクスポート =====
router.get('/docx/:id', async (req, res) => {
  try {
    const data = await getRecordingFullData(req.params.id);
    if (!data) { res.status(404).json({ error: '見つかりません' }); return; }

    const children: any[] = [];

    // タイトル
    children.push(new Paragraph({
      children: [new TextRun({ text: `議事録: ${data.recording.file_name}`, bold: true, size: 32 })],
      heading: HeadingLevel.TITLE,
    }));

    // 概要
    children.push(new Paragraph({
      children: [new TextRun({ text: '概要', bold: true, size: 28 })],
      heading: HeadingLevel.HEADING_1,
    }));
    children.push(new Paragraph({ children: [new TextRun(`ファイル: ${data.recording.file_name}`)] }));
    children.push(new Paragraph({ children: [new TextRun(`長さ: ${formatTime(data.recording.duration_seconds as number)}`)] }));
    children.push(new Paragraph({ children: [new TextRun(`モード: ${data.recording.audio_mode === 'face_to_face' ? '対面録音' : data.recording.audio_mode === 'phone_call' ? '通話録音' : '自動'}`)] }));
    children.push(new Paragraph({ children: [new TextRun(`作成日: ${data.recording.created_at}`)] }));
    children.push(new Paragraph({ text: '' }));

    // 要約
    for (const summary of data.summaries) {
      const label = summaryTypeLabels[summary.summary_type] || summary.summary_type;
      children.push(new Paragraph({
        children: [new TextRun({ text: label, bold: true, size: 28 })],
        heading: HeadingLevel.HEADING_1,
      }));
      const lines = (summary.content as string).split('\n');
      for (const line of lines) {
        children.push(new Paragraph({ children: [new TextRun(line)] }));
      }
      children.push(new Paragraph({ text: '' }));
    }

    // セクション
    if (data.sections.length > 0) {
      children.push(new Paragraph({
        children: [new TextRun({ text: 'セクション', bold: true, size: 28 })],
        heading: HeadingLevel.HEADING_1,
      }));
      for (const sec of data.sections) {
        children.push(new Paragraph({
          children: [new TextRun({ text: `${(sec.section_index as number) + 1}. ${sec.title} [${formatTime(sec.start_time as number)} - ${formatTime(sec.end_time as number)}]`, bold: true, size: 24 })],
          heading: HeadingLevel.HEADING_2,
        }));
        children.push(new Paragraph({ children: [new TextRun(sec.summary as string)] }));
        if (sec.user_comment) {
          children.push(new Paragraph({ children: [new TextRun({ text: `コメント: ${sec.user_comment}`, italics: true })] }));
        }
        children.push(new Paragraph({ text: '' }));
      }
    }

    // 文字起こし全文
    if (data.transcription) {
      children.push(new Paragraph({
        children: [new TextRun({ text: '文字起こし全文', bold: true, size: 28 })],
        heading: HeadingLevel.HEADING_1,
      }));
      for (const seg of data.transcription.segments) {
        const prefix = seg.speaker ? `[${formatTime(seg.start)}] ${seg.speaker}: ` : `[${formatTime(seg.start)}] `;
        children.push(new Paragraph({
          children: [
            new TextRun({ text: prefix, bold: true, size: 20 }),
            new TextRun({ text: seg.text, size: 20 }),
          ],
        }));
      }
    }

    // Q&A
    if (data.chatMessages.length > 0) {
      children.push(new Paragraph({ text: '' }));
      children.push(new Paragraph({
        children: [new TextRun({ text: 'Q&A', bold: true, size: 28 })],
        heading: HeadingLevel.HEADING_1,
      }));
      for (const msg of data.chatMessages) {
        const label = msg.role === 'user' ? 'Q: ' : 'A: ';
        children.push(new Paragraph({
          children: [
            new TextRun({ text: label, bold: true }),
            new TextRun(msg.content as string),
          ],
        }));
      }
    }

    const doc = new Document({ sections: [{ children }] });
    const buffer = await Packer.toBuffer(doc);
    const fileName = encodeURIComponent(data.recording.file_name?.toString().replace(/\.\w+$/, '') || 'export') + '.docx';

    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
    res.send(buffer);
  } catch (err: any) {
    console.error('Wordエクスポートエラー:', err);
    res.status(500).json({ error: err.message });
  }
});

// ===== 再読み込み用JSON (.json) エクスポート（圧縮） =====
router.get('/json/:id', async (req, res) => {
  try {
    const data = await getRecordingFullData(req.params.id);
    if (!data) { res.status(404).json({ error: '見つかりません' }); return; }

    // 動画・音声ファイルパスは除外（テキストデータのみ）
    const exportData = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      recording: {
        file_name: data.recording.file_name,
        duration_seconds: data.recording.duration_seconds,
        audio_mode: data.recording.audio_mode,
        is_video: data.recording.is_video,
        mime_type: data.recording.mime_type,
        created_at: data.recording.created_at,
      },
      transcription: data.transcription ? {
        full_text: data.transcription.full_text,
        segments: data.transcription.segments,
        language: data.transcription.language,
      } : null,
      summaries: data.summaries.map(s => ({
        summary_type: s.summary_type,
        content: s.content,
      })),
      sections: data.sections.map(s => ({
        section_index: s.section_index,
        title: s.title,
        start_time: s.start_time,
        end_time: s.end_time,
        transcript_text: s.transcript_text,
        summary: s.summary,
        mindmap_mermaid: s.mindmap_mermaid,
        user_comment: s.user_comment,
      })),
      chatMessages: data.chatMessages.map(c => ({
        role: c.role,
        content: c.content,
        created_at: c.created_at,
      })),
      mindmaps: data.mindmaps.map(m => ({
        section_id: m.section_id,
        mermaid_code: m.mermaid_code,
      })),
    };

    const jsonStr = JSON.stringify(exportData);
    const compressed = await gzip(Buffer.from(jsonStr));

    const fileName = encodeURIComponent(data.recording.file_name?.toString().replace(/\.\w+$/, '') || 'export') + '.mt.json.gz';

    res.setHeader('Content-Type', 'application/gzip');
    res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
    res.send(compressed);
  } catch (err: any) {
    console.error('JSONエクスポートエラー:', err);
    res.status(500).json({ error: err.message });
  }
});

export default router;
