import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import { parseSmc2 } from '../services/smc2Parser';
import { parseCsvVariables } from '../services/csvParser';
import { parseStText } from '../services/stParser';
import { parsePdf } from '../services/pdfParser';
import { mergeProjectData } from '../services/fileMerger';
import { saveAnalysis } from '../db/sqlite';

const router = Router();

// アップロードディレクトリ
const uploadDir = path.join(process.cwd(), 'uploads');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

const storage = multer.memoryStorage();
const upload = multer({
  storage,
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB
    files: 20,
  },
});

router.post('/', upload.array('files', 20), async (req, res) => {
  try {
    const files = req.files as Express.Multer.File[];
    if (!files || files.length === 0) {
      res.status(400).json({ error: 'ファイルがありません' });
      return;
    }

    const projectId = uuidv4();
    let smc2Project = null;
    const csvVariables: any[] = [];
    let stResult = null;
    let pdfText: string | null = null;
    const uploadedFiles: any[] = [];
    const imageFiles: { name: string; base64: string; mediaType: string }[] = [];

    for (const file of files) {
      const ext = path.extname(file.originalname).toLowerCase();
      const fileId = uuidv4();

      let fileType = 'unknown';

      switch (ext) {
        case '.smc2': {
          fileType = 'smc2';
          smc2Project = await parseSmc2(file.buffer, file.originalname);
          break;
        }
        case '.csv': {
          fileType = 'csv';
          const content = file.buffer.toString('utf-8');
          const vars = parseCsvVariables(content);
          csvVariables.push(...vars);
          break;
        }
        case '.st':
        case '.txt': {
          fileType = ext === '.st' ? 'st' : 'txt';
          const content = file.buffer.toString('utf-8');
          stResult = parseStText(content, file.originalname);
          break;
        }
        case '.pdf': {
          fileType = 'pdf';
          const result = await parsePdf(file.buffer);
          if (result.text) {
            pdfText = result.text;
          }
          break;
        }
        case '.png':
        case '.jpg':
        case '.jpeg': {
          fileType = 'image';
          const base64 = file.buffer.toString('base64');
          const mediaType = ext === '.png' ? 'image/png' : 'image/jpeg';
          imageFiles.push({ name: file.originalname, base64, mediaType });
          break;
        }
      }

      uploadedFiles.push({
        id: fileId,
        name: file.originalname,
        type: fileType,
        size: file.size,
        uploadedAt: new Date().toISOString(),
      });
    }

    // データ統合
    const mergedProject = mergeProjectData(smc2Project, csvVariables, stResult, pdfText);

    // DB保存
    await saveAnalysis(
      projectId,
      mergedProject.projectInfo.name,
      mergedProject,
      null,
      files.map((f) => f.originalname),
    );

    // レスポンス
    const response = {
      files: uploadedFiles,
      smc2Project: mergedProject,
      analysisResult: null,
      screenshotAnalyses: null,
      projectId,
      imageFiles: imageFiles.map((f) => f.name),
    };

    res.json(response);
  } catch (err) {
    console.error('アップロードエラー:', err);
    res.status(500).json({ error: 'ファイル処理中にエラーが発生しました', details: String(err) });
  }
});

export default router;
