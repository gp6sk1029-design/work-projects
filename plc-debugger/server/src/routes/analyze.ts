import { Router } from 'express';
import { ClaudeService } from '../services/claudeService';
import { checkCrossReference, checkAlarmCoverage } from '../services/hmiCrossChecker';
import { getAnalysisById, saveAnalysis, saveDb } from '../db/sqlite';

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

    // Claude APIで分析
    const claude = new ClaudeService(apiKey);
    const analysisResult = await claude.analyzeBugs(project);

    // クロスリファレンスチェック（ローカル）
    const crossRef = checkCrossReference(project);
    const alarmCoverage = checkAlarmCoverage(project);

    // ローカルチェック結果をマージ
    if (!analysisResult.hmiAnalysis) {
      analysisResult.hmiAnalysis = {};
    }
    if (!analysisResult.hmiAnalysis.crossReference) {
      analysisResult.hmiAnalysis.crossReference = crossRef;
    }
    if (!analysisResult.hmiAnalysis.alarmCoverage) {
      analysisResult.hmiAnalysis.alarmCoverage = alarmCoverage;
    }

    // DB更新
    await saveAnalysis(
      projectId,
      record.projectName,
      project,
      analysisResult,
      record.fileNames,
    );

    res.json(analysisResult);
  } catch (err) {
    console.error('分析エラー:', err);
    res.status(500).json({ error: '分析中にエラーが発生しました', details: String(err) });
  }
});

export default router;
