import { Router } from 'express';
import path from 'path';
import fs from 'fs';
import { runPythonCli, ensureDir } from '../pythonRunner';

const router = Router();

const LEARN_DIR = path.resolve(__dirname, '../../uploads/learn');
ensureDir(LEARN_DIR);

interface SampleItem {
  batchId: string;        // 親フォルダ名（アップロード時刻＋ハッシュ）
  filename: string;       // ファイル名（UTF-8）
  uploaded_at: string;    // ISO文字列
  size_bytes: number;
  path: string;           // フルパス（内部用・レスポンスには含めない）
}

function scanSamples(): SampleItem[] {
  if (!fs.existsSync(LEARN_DIR)) return [];
  const out: SampleItem[] = [];
  const batches = fs.readdirSync(LEARN_DIR, { withFileTypes: true });
  for (const b of batches) {
    if (!b.isDirectory()) continue;
    const batchPath = path.join(LEARN_DIR, b.name);
    const files = fs.readdirSync(batchPath, { withFileTypes: true });
    for (const f of files) {
      if (!f.isFile()) continue;
      const fullPath = path.join(batchPath, f.name);
      try {
        const stat = fs.statSync(fullPath);
        out.push({
          batchId: b.name,
          filename: f.name,
          uploaded_at: stat.mtime.toISOString(),
          size_bytes: stat.size,
          path: fullPath,
        });
      } catch {
        // skip unreadable
      }
    }
  }
  // 新しい順
  out.sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at));
  return out;
}

/**
 * GET /api/samples
 * 現在学習対象になっているサンプル図面の一覧
 */
router.get('/', (_req, res) => {
  try {
    const items = scanSamples();
    res.json({
      count: items.length,
      totalBytes: items.reduce((s, i) => s + i.size_bytes, 0),
      items: items.map((i) => ({
        batchId: i.batchId,
        filename: i.filename,
        uploaded_at: i.uploaded_at,
        size_bytes: i.size_bytes,
        // プレビュー用URL
        url: `/api/samples/file/${encodeURIComponent(i.batchId)}/${encodeURIComponent(i.filename)}`,
      })),
    });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

/**
 * GET /api/samples/file/:batchId/:filename
 * サンプル図面のプレビュー取得
 */
router.get('/file/:batchId/:filename', (req, res) => {
  const { batchId, filename } = req.params;
  const filePath = path.resolve(LEARN_DIR, batchId, filename);
  // パストラバーサル対策
  if (!filePath.startsWith(path.resolve(LEARN_DIR))) {
    return res.status(403).json({ error: 'forbidden' });
  }
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'not found' });
  }
  const ext = path.extname(filePath).toLowerCase();
  const mime =
    ext === '.pdf' ? 'application/pdf'
    : ext === '.png' ? 'image/png'
    : ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg'
    : 'application/octet-stream';
  res.setHeader('Content-Type', mime);
  res.setHeader('Content-Disposition', `inline; filename="${encodeURIComponent(filename)}"`);
  fs.createReadStream(filePath).pipe(res);
});

/**
 * DELETE /api/samples/:batchId/:filename
 * 悪いサンプルを削除
 */
router.delete('/:batchId/:filename', (req, res) => {
  const { batchId, filename } = req.params;
  const filePath = path.resolve(LEARN_DIR, batchId, filename);
  if (!filePath.startsWith(path.resolve(LEARN_DIR))) {
    return res.status(403).json({ error: 'forbidden' });
  }
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'not found' });
  }
  try {
    fs.unlinkSync(filePath);

    // バッチフォルダが空になったら削除
    const batchDir = path.join(LEARN_DIR, batchId);
    try {
      const remaining = fs.readdirSync(batchDir);
      if (remaining.length === 0) fs.rmdirSync(batchDir);
    } catch {}

    res.json({ ok: true, deleted: filename });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

/**
 * POST /api/samples/relearn
 * 残っている全サンプルを対象に再学習を実行
 * body: { noAi?: boolean }
 */
router.post('/relearn', async (req, res) => {
  const noAi = req.body?.noAi === true || req.body?.noAi === 'true';

  const items = scanSamples();
  if (items.length === 0) {
    return res.status(400).json({
      error: 'サンプルが1枚もありません。学習を実行できません。',
    });
  }

  try {
    // 複数バッチフォルダを学習コマンドに渡す
    const args = ['learn', ...items.map((i) => i.path)];
    if (noAi) args.push('--no-ai');

    const result = await runPythonCli(args, 600_000);

    const ROOT = path.resolve(__dirname, '../../..');
    const learnedPath = path.join(ROOT, 'config', 'learned_rules.json');
    let learned: any = null;
    if (fs.existsSync(learnedPath)) {
      learned = JSON.parse(fs.readFileSync(learnedPath, 'utf-8'));
    }

    res.json({
      ok: result.exitCode === 0,
      exitCode: result.exitCode,
      filesLearned: items.length,
      rulesCount: learned?.rules?.length || 0,
      stderr: result.stderr.slice(-2000),
      learned,
    });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

/**
 * DELETE /api/samples (全削除)
 * 全サンプルとlearned_rules.jsonをリセット
 */
router.delete('/', (_req, res) => {
  try {
    // learn配下の全バッチを削除
    if (fs.existsSync(LEARN_DIR)) {
      const batches = fs.readdirSync(LEARN_DIR, { withFileTypes: true });
      for (const b of batches) {
        if (b.isDirectory()) {
          fs.rmSync(path.join(LEARN_DIR, b.name), { recursive: true, force: true });
        }
      }
    }
    // learned_rules.jsonも削除
    const ROOT = path.resolve(__dirname, '../../..');
    const learnedPath = path.join(ROOT, 'config', 'learned_rules.json');
    if (fs.existsSync(learnedPath)) fs.unlinkSync(learnedPath);

    res.json({ ok: true });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

export default router;
