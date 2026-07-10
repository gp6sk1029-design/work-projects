/**
 * PDF差分エンジン（Python pdf_diff.py）の起動・結果取得
 *  plc-debugger と同じパターン:
 *   - JSON は stdout に UTF-8 で
 *   - ログは stderr に分離
 */
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

const PYTHON_SCRIPT = path.resolve(__dirname, '..', '..', 'python', 'pdf_diff.py');

export interface PdfDiffResult {
  pagesA: any[];
  pagesB: any[];
  matches: any[];
  summary: {
    pagesA: number;
    pagesB: number;
    exactMatches: number;
    similarMatches: number;
    onlyInA: number;
    onlyInB: number;
  };
}

export function runPdfDiff(pdfA: string, pdfB: string, outDir: string): Promise<PdfDiffResult> {
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  return new Promise((resolve, reject) => {
    const args = [
      PYTHON_SCRIPT,
      '--pdf-a', pdfA,
      '--pdf-b', pdfB,
      '--out-dir', outDir,
    ];
    const proc = spawn('python', args, {
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
      windowsHide: true,
    });

    const stdoutChunks: Buffer[] = [];
    let stderrText = '';

    proc.stdout.on('data', (chunk) => stdoutChunks.push(chunk));
    proc.stderr.on('data', (chunk) => {
      stderrText += chunk.toString('utf-8');
      // ログは透過的に出す
      process.stderr.write(`[pdf_diff.py] ${chunk}`);
    });

    proc.on('error', (err) => {
      reject(new Error(`Pythonプロセス起動失敗: ${err.message}\nstderr:\n${stderrText}`));
    });

    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`pdf_diff.py が異常終了 (exit=${code})\nstderr:\n${stderrText}`));
        return;
      }
      const jsonText = Buffer.concat(stdoutChunks).toString('utf-8');
      try {
        const data = JSON.parse(jsonText) as PdfDiffResult;
        resolve(data);
      } catch (err) {
        reject(new Error(`JSONパース失敗: ${(err as Error).message}\n先頭500字: ${jsonText.substring(0, 500)}`));
      }
    });
  });
}
