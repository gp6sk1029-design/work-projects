import { Router } from 'express';
import { ClaudeService } from '../services/claudeService';
import { getAnalysisById } from '../db/sqlite';

const router = Router();

router.post('/', async (req, res) => {
  try {
    const { projectId, images } = req.body;
    if (!projectId) {
      res.status(400).json({ error: 'projectId が必要です' });
      return;
    }
    if (!images || !Array.isArray(images) || images.length === 0) {
      res.status(400).json({ error: 'スクリーンショットを1枚以上添付してください' });
      return;
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: 'GEMINI_API_KEY が設定されていません' });
      return;
    }

    const record = await getAnalysisById(projectId);
    if (!record) {
      res.status(404).json({ error: 'プロジェクトが見つかりません' });
      return;
    }

    const project = record.projectData;
    const claude = new ClaudeService(apiKey);
    const diagnosisResult = await claude.comprehensiveDiagnosis(project, images);

    res.json(diagnosisResult);
  } catch (err) {
    console.error('総合診断エラー:', err);
    res.status(500).json({ error: '総合診断中にエラーが発生しました', details: String(err) });
  }
});

export default router;
