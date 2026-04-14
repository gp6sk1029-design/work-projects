import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import uploadRouter from './routes/upload';
import analyzeRouter from './routes/analyze';
import troubleshootRouter from './routes/troubleshoot';
import hmiAnalyzeRouter from './routes/hmiAnalyze';
import generateRouter from './routes/generate';
import analyzeProgramRouter from './routes/analyzeProgram';
import diagnosisRouter from './routes/diagnosis';
import { getAnalysisHistory, getAnalysisById } from './db/sqlite';

// 複数パスで .env を読み込む
dotenv.config();
dotenv.config({ path: path.resolve(process.cwd(), '.env') });
dotenv.config({ path: path.resolve(__dirname, '../.env') });
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// API ルート
app.use('/api/upload', uploadRouter);
app.use('/api/analyze', analyzeRouter);
app.use('/api/troubleshoot', troubleshootRouter);
app.use('/api/hmi-analyze', hmiAnalyzeRouter);
app.use('/api/generate', generateRouter);
app.use('/api/analyze-program', analyzeProgramRouter);
app.use('/api/diagnosis', diagnosisRouter);

// 分析履歴
app.get('/api/history', async (_req, res) => {
  try {
    const history = await getAnalysisHistory();
    res.json(history);
  } catch (err) {
    res.status(500).json({ error: '履歴取得エラー' });
  }
});

app.get('/api/history/:id', async (req, res) => {
  try {
    const record = await getAnalysisById(req.params.id);
    if (!record) {
      res.status(404).json({ error: '見つかりません' });
      return;
    }
    res.json(record);
  } catch (err) {
    res.status(500).json({ error: '履歴取得エラー' });
  }
});

// ヘルスチェック
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 本番環境では静的ファイルを配信
if (process.env.NODE_ENV === 'production') {
  const clientDist = path.join(__dirname, '../../client/dist');
  app.use(express.static(clientDist));
  app.get('*', (_req, res) => {
    res.sendFile(path.join(clientDist, 'index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`PLC Craft AI サーバー起動: http://localhost:${PORT}`);
});
