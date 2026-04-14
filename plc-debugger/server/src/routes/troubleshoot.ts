import { Router } from 'express';
import { ClaudeService } from '../services/claudeService';
import { getAnalysisById } from '../db/sqlite';

const router = Router();

router.post('/', async (req, res) => {
  try {
    const { message, images, history, projectId } = req.body;

    if (!message && (!images || images.length === 0)) {
      res.status(400).json({ error: 'メッセージまたは画像が必要です' });
      return;
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: 'GEMINI_API_KEY が設定されていません' });
      return;
    }

    // プロジェクトデータの取得
    let project = null;
    if (projectId) {
      const record = await getAnalysisById(projectId);
      if (record) {
        project = record.projectData;
      }
    }

    const claude = new ClaudeService(apiKey);
    const response = await claude.troubleshoot(
      message || '添付画像を確認してください。',
      project,
      history || [],
      images,
    );

    res.json({ response });
  } catch (err) {
    console.error('トラブルシュートエラー:', err);
    res.status(500).json({ error: 'トラブルシュート中にエラーが発生しました', details: String(err) });
  }
});

export default router;
