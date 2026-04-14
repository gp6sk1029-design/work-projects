import { Router } from 'express';
import { ClaudeService } from '../services/claudeService';

const router = Router();

// PLCプログラム生成エンドポイント
router.post('/', async (req, res) => {
  try {
    const { description, language, controllerType } = req.body;

    // 入力バリデーション
    if (!description) {
      res.status(400).json({ error: 'description（プログラムの要件説明）が必要です' });
      return;
    }

    if (!language || !['ST', 'LD'].includes(language)) {
      res.status(400).json({ error: "language は 'ST' または 'LD' を指定してください" });
      return;
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: 'GEMINI_API_KEY が設定されていません' });
      return;
    }

    // Gemini APIでプログラム生成
    const claude = new ClaudeService(apiKey);
    const result = await claude.generateProgram(description, language, controllerType || 'NX102');

    res.json(result);
  } catch (err) {
    console.error('プログラム生成エラー:', err);
    res.status(500).json({ error: 'プログラム生成中にエラーが発生しました', details: String(err) });
  }
});

export default router;
