import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { getDb, saveDb } from '../db/sqlite';
import { getMediaInfo } from '../services/ffmpegService';
import { detectAudioMode } from '../services/audioAnalyzer';

const storage = multer.diskStorage({
  destination: path.join(process.cwd(), 'uploads'),
  filename: (_req, file, cb) => {
    // 元のファイル名を保持（日本語対応）
    const ext = path.extname(file.originalname);
    const name = path.basename(file.originalname, ext);
    const safeName = `${Date.now()}_${name}${ext}`;
    cb(null, safeName);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 2 * 1024 * 1024 * 1024 }, // 2GB
  fileFilter: (_req, file, cb) => {
    const allowed = /^(audio|video)\//;
    if (allowed.test(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('音声または動画ファイルのみアップロード可能です'));
    }
  },
});

const router = Router();

router.post('/', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      res.status(400).json({ error: 'ファイルが見つかりません' });
      return;
    }

    const filePath = req.file.path;
    const mimeType = req.file.mimetype;

    // メディア情報取得
    const mediaInfo = await getMediaInfo(filePath);

    // デュアルモード判別
    const audioMode = detectAudioMode(mediaInfo);

    const id = uuidv4();
    const now = new Date().toISOString();

    // DB保存
    const db = await getDb();
    db.run(
      `INSERT INTO recordings (id, file_name, file_path, file_size, mime_type, duration_seconds, audio_mode, audio_analysis, is_video, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        req.file.filename,
        filePath,
        req.file.size,
        mimeType,
        mediaInfo.duration,
        audioMode,
        JSON.stringify(mediaInfo),
        mediaInfo.isVideo ? 1 : 0,
        now,
        now,
      ],
    );
    saveDb();

    res.json({
      id,
      file_name: req.file.filename,
      file_path: filePath,
      file_size: req.file.size,
      mime_type: mimeType,
      duration_seconds: mediaInfo.duration,
      audio_mode: audioMode,
      audio_analysis: JSON.stringify(mediaInfo),
      is_video: mediaInfo.isVideo,
      created_at: now,
      updated_at: now,
    });
  } catch (err: any) {
    console.error('アップロードエラー:', err);
    res.status(500).json({ error: err.message || 'アップロードに失敗しました' });
  }
});

export default router;
