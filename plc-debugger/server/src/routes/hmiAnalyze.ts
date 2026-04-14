import { Router } from 'express';
import { ClaudeService } from '../services/claudeService';
import { analyzeHmiScreenshot } from '../services/hmiVisionAnalyzer';
import { getAnalysisById } from '../db/sqlite';

const router = Router();

// HMIスクリーンショット分析
router.post('/screenshot', async (req, res) => {
  try {
    const { imageBase64, mediaType, projectId } = req.body;

    if (!imageBase64) {
      res.status(400).json({ error: '画像データが必要です' });
      return;
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: 'GEMINI_API_KEY が設定されていません' });
      return;
    }

    // TODO: HMIスクリーンショット分析のGemini対応
    const analysis = {
      screenName: 'スクリーンショット分析',
      detectedElements: [],
      layoutIssues: [],
      uxIssues: [],
      safetyIssues: ['スクリーンショット分析は現在準備中です'],
    };

    res.json(analysis);
  } catch (err) {
    console.error('スクリーンショット分析エラー:', err);
    res.status(500).json({ error: 'スクリーンショット分析中にエラーが発生しました' });
  }
});

export default router;
