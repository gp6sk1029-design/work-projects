import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

const ROOT = path.resolve(__dirname, '../..');
const SRC_DIR = path.join(ROOT, 'src');

function resolvePython(): string {
  // 環境変数優先、なければ python（Windows既定）
  return process.env.PYTHON_PATH || 'python';
}

export interface PythonRunResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

/**
 * drawing-checkerのPython CLIを呼び出す
 * PYTHONPATH に src を追加して `python -m drawing_checker ...` を実行
 */
export function runPythonCli(args: string[], timeoutMs = 180_000): Promise<PythonRunResult> {
  return new Promise((resolve, reject) => {
    const env = { ...process.env };
    const existingPP = env.PYTHONPATH || '';
    env.PYTHONPATH = SRC_DIR + (existingPP ? path.delimiter + existingPP : '');
    env.PYTHONIOENCODING = 'utf-8';

    const py = resolvePython();
    const proc = spawn(py, ['-m', 'drawing_checker', ...args], {
      cwd: ROOT,
      env,
      windowsHide: true,
    });

    let stdout = Buffer.alloc(0);
    let stderr = '';
    proc.stdout.on('data', (chunk) => {
      stdout = Buffer.concat([stdout, chunk]);
    });
    proc.stderr.on('data', (chunk) => {
      stderr += chunk.toString('utf-8');
    });

    const timer = setTimeout(() => {
      proc.kill();
      reject(new Error(`Python CLI timeout (${timeoutMs}ms)`));
    }, timeoutMs);

    proc.on('close', (code) => {
      clearTimeout(timer);
      resolve({
        stdout: stdout.toString('utf-8'),
        stderr,
        exitCode: code ?? -1,
      });
    });

    proc.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}

/**
 * stdoutからJSON本体だけを抽出（前置ログ等を除去）
 */
export function extractJson(raw: string): any {
  const trimmed = raw.trim();
  // 最後の '{' または '[' から末尾までを試す
  const lastBrace = Math.max(trimmed.lastIndexOf('{'), trimmed.lastIndexOf('['));
  // 先頭の '{' or '['
  const firstBrace = Math.min(
    ...[trimmed.indexOf('{'), trimmed.indexOf('[')].filter(i => i >= 0)
  );
  if (firstBrace < 0) {
    throw new Error('JSON出力が見つかりません: ' + trimmed.slice(0, 200));
  }
  const body = trimmed.slice(firstBrace);
  try {
    return JSON.parse(body);
  } catch {
    // 最後の '}' までで試す
    const lastBraceClose = body.lastIndexOf('}');
    return JSON.parse(body.slice(0, lastBraceClose + 1));
  }
}

export function ensureDir(p: string): void {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}
