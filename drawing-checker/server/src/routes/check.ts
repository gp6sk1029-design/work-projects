import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import { runPythonCli, extractJson, ensureDir } from '../pythonRunner';

const router = Router();

const UPLOADS_DIR = path.resolve(__dirname, '../../uploads');
const RESULTS_DIR = path.resolve(__dirname, '../../results');
ensureDir(UPLOADS_DIR);
ensureDir(RESULTS_DIR);

// ファイル名のUTF-8化とユニーク化
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_DIR),
  filename: (_req, file, cb) => {
    // multerがlatin1で受け取るのをUTF-8に直す
    const originalName = Buffer.from(file.originalname, 'latin1').toString('utf-8');
    const id = crypto.randomBytes(6).toString('hex');
    const ext = path.extname(originalName);
    const base = path.basename(originalName, ext);
    cb(null, `${Date.now()}_${id}_${base}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 100 * 1024 * 1024 }, // 100MB
});

/**
 * POST /api/check
 * form-data:
 *   file: 図面ファイル
 *   ai: "true" でAI補完レイヤー有効
 * レスポンス:
 *   { ok, results: [...], resultId, pdfUrl, pdfName }
 */
router.post('/', upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'ファイルが添付されていません' });
  }

  const useAi = req.body.ai === 'true';
  const uploadedPath = req.file.path;

  // 結果ごとに隔離したフォルダ（同名ファイルで上書きされないように）
  const resultId = path.basename(uploadedPath, path.extname(uploadedPath));
  const resultDir = path.join(RESULTS_DIR, resultId);
  ensureDir(resultDir);

  try {
    const args = [
      'check', uploadedPath,
      '--json',
      '--no-html',
      '--output-dir', resultDir,
    ];
    if (useAi) args.push('--ai');

    const result = await runPythonCli(args);

    // exit code は 0=合格, 1=不合格, 2=エラー。ただし --json はどちらもJSONを返す
    let parsed: any = null;
    try {
      parsed = extractJson(result.stdout);
    } catch (e: any) {
      return res.status(500).json({
        error: 'Python CLIの出力が読めません',
        stderr: result.stderr.slice(-2000),
        stdout: result.stdout.slice(-500),
      });
    }

    if (parsed.error) {
      return res.status(400).json({ error: parsed.error, stderr: result.stderr.slice(-2000) });
    }

    const first = parsed.results?.[0];
    // 注釈PDFのURLを付与
    let pdfUrl: string | null = null;
    let pdfName: string | null = null;
    if (first?.checked_pdf_path && fs.existsSync(first.checked_pdf_path)) {
      pdfName = path.basename(first.checked_pdf_path);
      pdfUrl = `/api/files/result/${resultId}/${encodeURIComponent(pdfName)}`;
    }

    // 元ファイルのURLも（プレビュー用）
    const originalName = path.basename(uploadedPath);
    const originalUrl = `/api/files/upload/${encodeURIComponent(originalName)}`;

    return res.json({
      ok: parsed.pass,
      resultId,
      result: first,
      pdfUrl,
      pdfName,
      originalUrl,
      originalName: req.file.originalname,
    });
  } catch (e: any) {
    console.error('check error:', e);
    return res.status(500).json({ error: e.message || 'unknown error' });
  }
});

export default router;
