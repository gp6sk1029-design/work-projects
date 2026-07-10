/**
 * 設備翻訳API
 *  - POST /api/translate          翻訳実行
 *  - GET  /api/translate/glossary 略語辞書一覧取得
 *  - POST /api/translate/glossary 略語辞書に追加
 *  - DELETE /api/translate/glossary/:id 略語辞書から削除
 */
import { Router } from 'express';
import { TranslationService } from '../services/translationService';
import {
  initGlossaryTable,
  listGlossary,
  upsertGlossary,
  deleteGlossary,
} from '../db/glossaryDb';

const router = Router();

// 起動時にテーブル初期化
initGlossaryTable().catch((err) => {
  console.error('glossaryテーブル初期化エラー:', err);
});

// 翻訳実行
router.post('/', async (req, res) => {
  try {
    const { text, direction, mode } = req.body;

    if (!text || typeof text !== 'string' || text.trim().length === 0) {
      res.status(400).json({ error: 'テキストが空です' });
      return;
    }
    if (text.length > 5000) {
      res.status(400).json({ error: 'テキストが長すぎます（5000文字以内）' });
      return;
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: 'GEMINI_API_KEY が設定されていません' });
      return;
    }

    const dir = direction === 'ja-en' || direction === 'en-ja' ? direction : 'auto';
    const md =
      mode === 'variable' || mode === 'abbr-lookup' ? mode : 'sentence';

    const service = new TranslationService(apiKey);
    const result = await service.translate(text, dir, md);
    res.json(result);
  } catch (err) {
    console.error('翻訳エラー:', err);
    res.status(500).json({ error: '翻訳中にエラーが発生しました', details: String(err) });
  }
});

// 辞書一覧
router.get('/glossary', async (_req, res) => {
  try {
    const list = await listGlossary();
    res.json(list);
  } catch (err) {
    console.error('辞書取得エラー:', err);
    res.status(500).json({ error: '辞書取得エラー' });
  }
});

// 辞書追加（フロントから「この訳を辞書に登録」ボタン）
router.post('/glossary', async (req, res) => {
  try {
    const { term_ja, term_en, abbr, category, note } = req.body;
    if (!term_ja || !term_en) {
      res.status(400).json({ error: 'term_ja と term_en は必須です' });
      return;
    }
    await upsertGlossary({
      term_ja: String(term_ja).trim(),
      term_en: String(term_en).trim(),
      abbr: String(abbr || '').trim(),
      category: String(category || 'その他').trim(),
      note: String(note || '').trim(),
    });
    res.json({ ok: true });
  } catch (err) {
    console.error('辞書追加エラー:', err);
    res.status(500).json({ error: '辞書追加エラー' });
  }
});

// 辞書削除
router.delete('/glossary/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      res.status(400).json({ error: 'IDが不正です' });
      return;
    }
    await deleteGlossary(id);
    res.json({ ok: true });
  } catch (err) {
    console.error('辞書削除エラー:', err);
    res.status(500).json({ error: '辞書削除エラー' });
  }
});

export default router;
