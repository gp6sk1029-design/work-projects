import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import { runPythonCli, ensureDir } from '../pythonRunner';

const router = Router();

const LEARN_DIR = path.resolve(__dirname, '../../uploads/learn');
ensureDir(LEARN_DIR);

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    // 1回のアップロードごとにサブフォルダ
    const batchId = (_req as any)._batchId
      || ((_req as any)._batchId = `${Date.now()}_${crypto.randomBytes(4).toString('hex')}`);
    const dir = path.join(LEARN_DIR, batchId);
    ensureDir(dir);
    cb(null, dir);
  },
  filename: (_req, file, cb) => {
    const original = Buffer.from(file.originalname, 'latin1').toString('utf-8');
    cb(null, original);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 100 * 1024 * 1024, files: 200 },
});

/**
 * POST /api/learn
 * form-data:
 *   files: サンプル図面（複数）
 *   noAi: "true" でAI補完を使わない
 */
router.post('/', upload.array('files', 200), async (req, res) => {
  const files = req.files as Express.Multer.File[] | undefined;
  if (!files || files.length === 0) {
    return res.status(400).json({ error: 'ファイルが添付されていません' });
  }

  const noAi = req.body.noAi === 'true';
  const batchDir = path.dirname(files[0].path);

  try {
    const args = ['learn', batchDir];
    if (noAi) args.push('--no-ai');

    const result = await runPythonCli(args, 600_000);

    // 結果：learned_rules.json の内容を返す
    const ROOT = path.resolve(__dirname, '../../..');
    const learnedPath = path.join(ROOT, 'config', 'learned_rules.json');
    let learned: any = null;
    if (fs.existsSync(learnedPath)) {
      learned = JSON.parse(fs.readFileSync(learnedPath, 'utf-8'));
    }

    return res.json({
      ok: result.exitCode === 0,
      exitCode: result.exitCode,
      filesLearned: files.length,
      rulesCount: learned?.rules?.length || 0,
      stderr: result.stderr.slice(-2000),
      learned,
    });
  } catch (e: any) {
    console.error('learn error:', e);
    return res.status(500).json({ error: e.message });
  }
});

export default router;
