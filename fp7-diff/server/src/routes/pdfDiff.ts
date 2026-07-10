/**
 * PDF差分APIエンドポイント
 *  POST /api/pdf-diff      2つのPDFをアップロード→差分エンジン実行
 *  GET  /api/pdf-diff/image/:jobId/:filename  生成画像配信
 */
import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import { runPdfDiff } from '../services/pdfDiffRunner';

const UPLOADS_DIR = path.join(process.cwd(), 'uploads', 'pdf');
const RESULTS_DIR = path.join(process.cwd(), 'results', 'pdf');
if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR, { recursive: true });
if (!fs.existsSync(RESULTS_DIR)) fs.mkdirSync(RESULTS_DIR, { recursive: true });

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_DIR),
  filename: (_req, file, cb) => {
    const original = Buffer.from(file.originalname, 'latin1').toString('utf-8');
    const id = crypto.randomBytes(6).toString('hex');
    const ext = path.extname(original) || '.pdf';
    const base = path.basename(original, ext).replace(/[^\w぀-ヿ一-鿿\-_]/g, '_');
    cb(null, `${Date.now()}_${id}_${base}${ext}`);
  },
});
const upload = multer({ storage, limits: { fileSize: 100 * 1024 * 1024 } });

const router = Router();

router.post(
  '/',
  upload.fields([
    { name: 'pdfA', maxCount: 1 },
    { name: 'pdfB', maxCount: 1 },
  ]),
  async (req, res) => {
    try {
      const files = req.files as { pdfA?: Express.Multer.File[]; pdfB?: Express.Multer.File[] };
      if (!files.pdfA?.[0] || !files.pdfB?.[0]) {
        res.status(400).json({ error: 'pdfA と pdfB の両方が必要です' });
        return;
      }
      const pdfA = files.pdfA[0];
      const pdfB = files.pdfB[0];

      const jobId = crypto.randomUUID();
      const outDir = path.join(RESULTS_DIR, jobId);

      const projectAName = Buffer.from(pdfA.originalname, 'latin1').toString('utf-8');
      const projectBName = Buffer.from(pdfB.originalname, 'latin1').toString('utf-8');

      console.log(`[PDF Diff] ${projectAName} vs ${projectBName} - jobId=${jobId}`);

      const result = await runPdfDiff(pdfA.path, pdfB.path, outDir);

      res.json({
        jobId,
        projectAName,
        projectBName,
        imageBaseUrl: `/api/pdf-diff/image/${jobId}`,
        ...result,
      });
    } catch (err) {
      console.error('PDF差分エラー:', err);
      res.status(500).json({ error: 'PDF差分処理中にエラー', details: String(err) });
    }
  },
);

// 生成画像配信
router.get('/image/:jobId/:filename', (req, res) => {
  const { jobId, filename } = req.params;
  // パストラバーサル対策
  if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
    res.status(400).send('Invalid filename');
    return;
  }
  if (!/^[\w-]+$/.test(jobId)) {
    res.status(400).send('Invalid jobId');
    return;
  }
  const filepath = path.join(RESULTS_DIR, jobId, filename);
  if (!fs.existsSync(filepath)) {
    res.status(404).send('Not found');
    return;
  }
  res.setHeader('Cache-Control', 'public, max-age=3600');
  res.sendFile(filepath);
});

export default router;
