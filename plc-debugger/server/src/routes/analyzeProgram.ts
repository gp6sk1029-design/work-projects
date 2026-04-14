import { Router } from 'express';
import { ClaudeService } from '../services/claudeService';
import { getAnalysisById } from '../db/sqlite';

const router = Router();

router.post('/', async (req, res) => {
  try {
    const { projectId } = req.body;
    if (!projectId) {
      res.status(400).json({ error: 'projectId が必要です' });
      return;
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: 'GEMINI_API_KEY が設定されていません' });
      return;
    }

    // DBからプロジェクトデータを取得
    const record = await getAnalysisById(projectId);
    if (!record) {
      res.status(404).json({ error: 'プロジェクトが見つかりません' });
      return;
    }

    const project = record.projectData;

    // Gemini APIでプログラム解析
    const claude = new ClaudeService(apiKey);
    const analysisResult = await claude.analyzeProgram(project);

    res.json(analysisResult);
  } catch (err) {
    console.error('プログラム解析エラー:', err);
    res.status(500).json({ error: 'プログラム解析中にエラーが発生しました', details: String(err) });
  }
});

export default router;
