import { execFile } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';
import type { AudioAnalysis } from '../types';

const execFileAsync = promisify(execFile);

// FFmpegのパスを検出してPATHに追加
function setupFfmpegPath(): void {
  // まずPATHに既にあるか確認
  try {
    require('child_process').execFileSync('ffprobe', ['-version'], { stdio: 'ignore' });
    console.log('FFmpeg: PATH上で検出');
    return;
  } catch {}

  // WinGetインストール先を探す
  const localAppData = process.env.LOCALAPPDATA || '';
  const wingetBase = path.join(localAppData, 'Microsoft', 'WinGet', 'Packages');

  try {
    if (fs.existsSync(wingetBase)) {
      const packages = fs.readdirSync(wingetBase);
      for (const pkg of packages) {
        if (pkg.toLowerCase().includes('ffmpeg')) {
          const pkgDir = path.join(wingetBase, pkg);
          // パッケージ内のbinディレクトリを探す
          const binPath = findBinDir(pkgDir, 5);
          if (binPath) {
            process.env.PATH = binPath + path.delimiter + (process.env.PATH || '');
            console.log(`FFmpeg検出: ${binPath}`);
            return;
          }
        }
      }
    }
  } catch {}

  console.log('警告: FFmpegが見つかりません');
}

function findBinDir(dir: string, depth: number): string | null {
  if (depth <= 0) return null;
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    // このディレクトリにffprobe.exeがあるか
    if (entries.some(e => e.isFile() && e.name.toLowerCase() === 'ffprobe.exe')) {
      return dir;
    }
    // サブディレクトリを探す
    for (const e of entries) {
      if (e.isDirectory()) {
        const found = findBinDir(path.join(dir, e.name), depth - 1);
        if (found) return found;
      }
    }
  } catch {}
  return null;
}

setupFfmpegPath();

// FFmpegの存在確認
export async function checkFfmpeg(): Promise<boolean> {
  try {
    await execFileAsync('ffmpeg', ['-version']);
    return true;
  } catch {
    return false;
  }
}

// メディア情報取得
export async function getMediaInfo(filePath: string): Promise<AudioAnalysis & { isVideo: boolean }> {
  const { stdout } = await execFileAsync('ffprobe', [
    '-v', 'quiet',
    '-print_format', 'json',
    '-show_format',
    '-show_streams',
    filePath,
  ]);

  const info = JSON.parse(stdout);
  const audioStream = info.streams?.find((s: any) => s.codec_type === 'audio');
  const videoStream = info.streams?.find((s: any) => s.codec_type === 'video');
  const format = info.format || {};

  return {
    sampleRate: audioStream ? parseInt(audioStream.sample_rate || '0') : 0,
    channels: audioStream ? parseInt(audioStream.channels || '0') : 0,
    bitrate: format.bit_rate ? parseInt(format.bit_rate) : 0,
    codec: audioStream?.codec_name || 'unknown',
    duration: parseFloat(format.duration || '0'),
    format: format.format_name || 'unknown',
    isVideo: !!videoStream && videoStream.codec_name !== 'mjpeg', // アルバムアート除外
  };
}

// 無音区間検出
export async function detectSilence(
  filePath: string,
  noiseThresholdDb: number = -30,
  minDurationSec: number = 3,
): Promise<{ start: number; end: number }[]> {
  try {
    const { stderr } = await execFileAsync('ffmpeg', [
      '-i', filePath,
      '-af', `silencedetect=noise=${noiseThresholdDb}dB:d=${minDurationSec}`,
      '-f', 'null',
      '-',
    ], { maxBuffer: 10 * 1024 * 1024 });

    const silences: { start: number; end: number }[] = [];
    const lines = stderr.split('\n');
    let currentStart: number | null = null;

    for (const line of lines) {
      const startMatch = line.match(/silence_start:\s*([\d.]+)/);
      const endMatch = line.match(/silence_end:\s*([\d.]+)/);

      if (startMatch) {
        currentStart = parseFloat(startMatch[1]);
      }
      if (endMatch && currentStart !== null) {
        silences.push({
          start: currentStart,
          end: parseFloat(endMatch[1]),
        });
        currentStart = null;
      }
    }

    return silences;
  } catch {
    return [];
  }
}

// ファイル分割（チャンク）
export async function splitFile(
  filePath: string,
  splitPoints: number[],
  outputDir: string,
): Promise<string[]> {
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const ext = path.extname(filePath);
  const chunks: string[] = [];
  const points = [0, ...splitPoints];

  for (let i = 0; i < points.length; i++) {
    const start = points[i];
    const outputPath = path.join(outputDir, `chunk_${i}${ext}`);
    const args = ['-i', filePath, '-ss', String(start)];

    if (i < points.length - 1) {
      args.push('-to', String(points[i + 1]));
    }

    args.push('-c', 'copy', '-y', outputPath);
    await execFileAsync('ffmpeg', args);
    chunks.push(outputPath);
  }

  return chunks;
}

// 動画圧縮（2GB超対応）
export async function compressVideo(
  inputPath: string,
  outputPath: string,
): Promise<void> {
  await execFileAsync('ffmpeg', [
    '-i', inputPath,
    '-vf', 'scale=-2:720',
    '-c:v', 'libx264',
    '-preset', 'fast',
    '-crf', '28',
    '-c:a', 'aac',
    '-b:a', '128k',
    '-y', outputPath,
  ], { timeout: 600000 }); // 10分タイムアウト
}

// 動画から音声のみ抽出（89MB動画 → 数MBのMP3）
export async function extractAudio(inputPath: string, outputPath: string): Promise<void> {
  await execFileAsync('ffmpeg', [
    '-i', inputPath,
    '-vn',              // 映像なし
    '-acodec', 'libmp3lame',
    '-ab', '128k',
    '-ar', '16000',     // 16kHz（文字起こしに十分）
    '-ac', '1',         // モノラル
    '-y', outputPath,
  ], { timeout: 300000 }); // 5分タイムアウト
}

// ファイルサイズ取得
export function getFileSize(filePath: string): number {
  return fs.statSync(filePath).size;
}
