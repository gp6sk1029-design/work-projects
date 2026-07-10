/**
 * 比較APIエンドポイント
 *  - POST /api/compare  2ファイルをアップロードして差分計算＋AI解説
 *  - GET  /api/history  履歴一覧
 */
import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import { parseGlobalDeviceFile } from '../services/globalDeviceParser';
import { calculateDiff } from '../services/diffCalculator';
import { AiSummarizer } from '../services/aiSummarizer';
import { saveCompareHistory, listCompareHistory } from '../db/sqlite';

const UPLOADS_DIR = path.join(process.cwd(), 'uploads');
if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR, { recursive: true });

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_DIR),
  filename: (_req, file, cb) => {
    // 日本語ファイル名対策
    const original = Buffer.from(file.originalname, 'latin1').toString('utf-8');
    const id = crypto.randomBytes(6).toString('hex');
    const ext = path.extname(original) || '.txt';
    const base = path.basename(original, ext).replace(/[^\w぀-ヿ一-鿿\-_]/g, '_');
    cb(null, `${Date.now()}_${id}_${base}${ext}`);
  },
});
const upload = multer({ storage, limits: { fileSize: 20 * 1024 * 1024 } });

const router = Router();

router.post(
  '/',
  upload.fields([
    { name: 'fileA', maxCount: 1 },
    { name: 'fileB', maxCount: 1 },
  ]),
  async (req, res) => {
    try {
      const files = req.files as { fileA?: Express.Multer.File[]; fileB?: Express.Multer.File[] };
      if (!files.fileA?.[0] || !files.fileB?.[0]) {
        res.status(400).json({ error: 'ファイルAとファイルBの両方が必要です' });
        return;
      }
      const fileA = files.fileA[0];
      const fileB = files.fileB[0];
      const useAi = req.body.useAi !== 'false';

      const projectAName = Buffer.from(fileA.originalname, 'latin1').toString('utf-8');
      const projectBName = Buffer.from(fileB.originalname, 'latin1').toString('utf-8');

      // パース
      let entriesA, entriesB;
      try {
        entriesA = parseGlobalDeviceFile(fileA.path);
        entriesB = parseGlobalDeviceFile(fileB.path);
      } catch (err) {
        res.status(400).json({ error: `ファイル解析に失敗しました: ${String(err)}` });
        return;
      }

      if (entriesA.length === 0 || entriesB.length === 0) {
        res.status(400).json({
          error: 'デバイス情報が抽出できませんでした。FPWIN GR7のグローバルデバイスエクスポートファイル(.txt)を確認してください。',
          debug: { countA: entriesA.length, countB: entriesB.length },
        });
        return;
      }

      // 差分計算
      const diff = calculateDiff(entriesA, entriesB, projectAName, projectBName);

      // AI解説（オプション）
      let aiSummary = null;
      if (useAi) {
        const apiKey = process.env.GEMINI_API_KEY;
        if (apiKey) {
          try {
            const summarizer = new AiSummarizer(apiKey);
            aiSummary = await summarizer.summarize(diff);
          } catch (err) {
            console.error('AI解説エラー（続行）:', err);
            aiSummary = { overview: 'AI解説の生成に失敗しました。', mainChanges: [], patterns: [], risks: [], recommendations: [] };
          }
        } else {
          aiSummary = { overview: 'GEMINI_API_KEYが未設定のためAI解説をスキップしました。', mainChanges: [], patterns: [], risks: [], recommendations: [] };
        }
      }

      // 履歴保存
      const id = crypto.randomUUID();
      await saveCompareHistory(id, projectAName, projectBName, diff.summary, diff.rows, aiSummary);

      res.json({
        id,
        diff,
        aiSummary,
      });
    } catch (err) {
      console.error('比較エラー:', err);
      res.status(500).json({ error: '比較処理中にエラー', details: String(err) });
    }
  },
);

router.get('/history', async (_req, res) => {
  try {
    const list = await listCompareHistory();
    res.json(list);
  } catch (err) {
    res.status(500).json({ error: '履歴取得エラー' });
  }
});

export default router;
