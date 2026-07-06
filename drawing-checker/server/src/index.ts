import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs';
import checkRouter from './routes/check';
import learnRouter from './routes/learn';
import filesRouter from './routes/files';
import samplesRouter from './routes/samples';

// .envを複数パスで試行
dotenv.config();
dotenv.config({ path: path.resolve(process.cwd(), '.env') });
dotenv.config({ path: path.resolve(__dirname, '../.env') });
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const app = express();
const PORT = process.env.PORT || 3001;

// ディレクトリ準備
const ROOT = path.resolve(__dirname, '../..');
const UPLOADS_DIR = path.join(__dirname, '../uploads');
const RESULTS_DIR = path.join(__dirname, '../results');
for (const d of [UPLOADS_DIR, RESULTS_DIR]) {
  if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
}

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// ルート
app.use('/api/check', checkRouter);
app.use('/api/learn', learnRouter);
app.use('/api/files', filesRouter);
app.use('/api/samples', samplesRouter);

// ヘルスチェック
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', version: '1.0.0' });
});

// 情報
app.get('/api/info', (_req, res) => {
  try {
    const configDir = path.join(ROOT, 'config');
    const jis = JSON.parse(fs.readFileSync(path.join(configDir, 'jis_rules.json'), 'utf-8'));
    const learnedPath = path.join(configDir, 'learned_rules.json');
    const learnedCount = fs.existsSync(learnedPath)
      ? (JSON.parse(fs.readFileSync(learnedPath, 'utf-8')).rules || []).length
      : 0;
    res.json({
      jisRulesCount: (jis.rules || []).length,
      learnedRulesCount: learnedCount,
      hasLearnedRules: learnedCount > 0,
    });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(PORT, () => {
  console.log(`[drawing-checker server] listening on http://localhost:${PORT}`);
});
