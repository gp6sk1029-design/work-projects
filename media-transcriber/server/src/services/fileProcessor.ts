import path from 'path';
import fs from 'fs';
import { getMediaInfo, splitFile, compressVideo, getFileSize, extractAudio } from './ffmpegService';
import { uploadToGemini } from './geminiService';

const MAX_GEMINI_FILE_SIZE = 2 * 1024 * 1024 * 1024; // 2GB
const CHUNK_DURATION_MINUTES = 15;

interface ProcessedFile {
  fileUri: string;
  mimeType: string;
  isChunked: boolean;
  chunks?: { fileUri: string; mimeType: string; offsetSeconds: number }[];
}

// ファイルをGeminiにアップロード準備
export async function processFileForGemini(
  filePath: string,
  mimeType: string,
  onProgress?: (message: string) => void,
): Promise<ProcessedFile> {
  const mediaInfo = await getMediaInfo(filePath);

  // 動画の場合は音声のみ抽出して高速化（89MB動画 → 数MBのMP3）
  let processPath = filePath;
  let processMimeType = mimeType;

  if (mediaInfo.isVideo) {
    onProgress?.('動画から音声を抽出中...');
    const audioPath = filePath.replace(/\.\w+$/, '_audio.mp3');
    await extractAudio(filePath, audioPath);
    const audioSize = getFileSize(audioPath);
    onProgress?.(`音声抽出完了（${Math.round(audioSize / 1024 / 1024)}MB）`);
    processPath = audioPath;
    processMimeType = 'audio/mpeg';
  }

  const fileSize = getFileSize(processPath);

  // 2GB超の場合は圧縮（音声抽出後はまず起きない）
  if (fileSize > MAX_GEMINI_FILE_SIZE) {
    onProgress?.('ファイルが2GBを超えているため圧縮中...');
    const compressedPath = filePath.replace(/(\.\w+)$/, '_compressed.mp4');
    await compressVideo(filePath, compressedPath);
    processPath = compressedPath;
    processMimeType = 'video/mp4';
    onProgress?.('圧縮完了');
  }

  // 60分超の場合はチャンク分割
  if (mediaInfo.duration > CHUNK_DURATION_MINUTES * 60) {
    onProgress?.(`${Math.round(mediaInfo.duration / 60)}分の長時間ファイル - チャンク分割中...`);
    return await processChunkedUpload(processPath, processMimeType, mediaInfo.duration, onProgress);
  }

  // 通常アップロード
  const fileUri = await uploadToGemini(processPath, processMimeType, onProgress);
  return { fileUri, mimeType: processMimeType, isChunked: false };
}

// チャンク分割アップロード
async function processChunkedUpload(
  filePath: string,
  mimeType: string,
  durationSeconds: number,
  onProgress?: (message: string) => void,
): Promise<ProcessedFile> {
  const chunkDuration = CHUNK_DURATION_MINUTES * 60;
  const numChunks = Math.ceil(durationSeconds / chunkDuration);
  const splitPoints: number[] = [];

  for (let i = 1; i < numChunks; i++) {
    splitPoints.push(i * chunkDuration);
  }

  const outputDir = path.join(path.dirname(filePath), 'chunks_' + Date.now());
  const chunkFiles = await splitFile(filePath, splitPoints, outputDir);

  const chunks: ProcessedFile['chunks'] = [];
  for (let i = 0; i < chunkFiles.length; i++) {
    onProgress?.(`チャンク ${i + 1}/${chunkFiles.length} をアップロード中...`);
    const fileUri = await uploadToGemini(chunkFiles[i], mimeType, undefined);
    chunks.push({
      fileUri,
      mimeType,
      offsetSeconds: i * chunkDuration,
    });
  }

  // 一時チャンクファイルを削除
  for (const f of chunkFiles) {
    try { fs.unlinkSync(f); } catch {}
  }
  try { fs.rmdirSync(outputDir); } catch {}

  onProgress?.('全チャンクのアップロード完了');
  return {
    fileUri: chunks[0].fileUri,
    mimeType,
    isChunked: true,
    chunks,
  };
}
