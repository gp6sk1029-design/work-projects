import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { getDb } from './db/sqlite';
import uploadRouter from './routes/upload';
import transcribeRouter from './routes/transcribe';
import summarizeRouter from './routes/summarize';
import chatRouter from './routes/chat';
import mindmapRouter from './routes/mindmap';
import sectionsRouter from './routes/sections';
import historyRouter from './routes/history';
import exportRouter from './routes/exportData';
import importRouter from './routes/importData';

// 複数パスで .env を読み込む
dotenv.config();
dotenv.config({ path: path.resolve(process.cwd(), '.env') });
dotenv.config({ path: path.resolve(__dirname, '../.env') });
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const app = express();
const PORT = process.env.PORT || 3002;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// アップロードファイルの静的配信（動画再生用）
app.use('/uploads', express.static(path.join(process.cwd(), 'uploads')));

// API ルート
app.use('/api/upload', uploadRouter);
app.use('/api/transcribe', transcribeRouter);
app.use('/api/summarize', summarizeRouter);
app.use('/api/chat', chatRouter);
app.use('/api/mindmap', mindmapRouter);
app.use('/api/sections', sectionsRouter);
app.use('/api/history', historyRouter);
app.use('/api/export', exportRouter);
app.use('/api/import', importRouter);

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

// DB初期化してからサーバー起動
getDb().then(() => {
  app.listen(PORT, () => {
    console.log(`Media Transcriber サーバー起動: http://localhost:${PORT}`);
  });
}).catch((err) => {
  console.error('DB初期化エラー:', err);
  process.exit(1);
});
