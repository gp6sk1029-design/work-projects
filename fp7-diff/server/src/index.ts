import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import compareRouter from './routes/compare';
import pdfDiffRouter from './routes/pdfDiff';

// 複数パスから .env 読み込み
dotenv.config();
dotenv.config({ path: path.resolve(process.cwd(), '.env') });
dotenv.config({ path: path.resolve(__dirname, '../.env') });
dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const app = express();
const PORT = process.env.PORT || 3002;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

app.use('/api/compare', compareRouter);
app.use('/api/pdf-diff', pdfDiffRouter);

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString(), service: 'fp7-diff' });
});

// 本番モード: ビルド済みフロント(client/dist)を配信し、Express単体で完結させる
// （vite 開発サーバを常駐させる必要をなくす）
if (process.env.NODE_ENV === 'production') {
  const clientDist = path.join(__dirname, '../../client/dist');
  app.use(express.static(clientDist));
  app.get('*', (_req, res) => {
    res.sendFile(path.join(clientDist, 'index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`FP7 Diff サーバー起動: http://localhost:${PORT}`);
  if (process.env.NODE_ENV === 'production') {
    console.log(`  本番モード: フロント配信込み → ブラウザで http://localhost:${PORT} を開いてください`);
  }
});
