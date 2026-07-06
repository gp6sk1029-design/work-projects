import { Router } from 'express';
import path from 'path';
import fs from 'fs';

const router = Router();

const UPLOADS_DIR = path.resolve(__dirname, '../../uploads');
const RESULTS_DIR = path.resolve(__dirname, '../../results');

function sendFileSafe(baseDir: string, relPath: string, res: any) {
  const resolved = path.resolve(baseDir, relPath);
  if (!resolved.startsWith(path.resolve(baseDir))) {
    return res.status(403).json({ error: 'forbidden' });
  }
  if (!fs.existsSync(resolved)) {
    return res.status(404).json({ error: 'not found' });
  }
  const ext = path.extname(resolved).toLowerCase();
  const mime =
    ext === '.pdf' ? 'application/pdf'
    : ext === '.png' ? 'image/png'
    : ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg'
    : 'application/octet-stream';
  res.setHeader('Content-Type', mime);
  res.setHeader('Content-Disposition', `inline; filename="${encodeURIComponent(path.basename(resolved))}"`);
  fs.createReadStream(resolved).pipe(res);
}

// アップロード元ファイル取得
router.get('/upload/:name', (req, res) => {
  sendFileSafe(UPLOADS_DIR, req.params.name, res);
});

// 結果PDF取得
router.get('/result/:id/:name', (req, res) => {
  sendFileSafe(RESULTS_DIR, path.join(req.params.id, req.params.name), res);
});

export default router;
