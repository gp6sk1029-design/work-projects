import type { AudioAnalysis, AudioMode } from '../types';

// 音声分析結果からデュアルモードを判別
export function detectAudioMode(analysis: AudioAnalysis): AudioMode {
  const { sampleRate, channels } = analysis;

  // 通話録音の特徴: 狭帯域(8kHz/16kHz)、モノラル
  if (sampleRate <= 16000 && channels === 1) {
    return 'phone_call';
  }

  // 対面録音の特徴: 広帯域(44.1kHz/48kHz)、ステレオ
  if (channels >= 2 || sampleRate >= 44100) {
    return 'face_to_face';
  }

  // デフォルト: 対面録音として扱う
  return 'face_to_face';
}

// モード別の処理パラメータ
export function getModeParams(mode: AudioMode) {
  switch (mode) {
    case 'phone_call':
      return {
        transcriptPrompt: `これは電話通話の録音です。2名の話者の会話を正確に文字起こししてください。
話者を「話者A」「話者B」として区別してください。
聞き取れない箇所は無視して、聞き取れた発言のみ記載してください。
背景雑音・機械音・ノイズの記載は一切不要です。`,
        silenceThresholdDb: -25,
        silenceMinDuration: 2,
        label: '通話録音',
        icon: 'phone',
      };

    case 'face_to_face':
      return {
        transcriptPrompt: `これは対面会議の録音です。複数の話者の発言を正確に文字起こししてください。
話者が区別できる場合は「話者A」「話者B」...として分けてください。
聞き取れない箇所は無視して、聞き取れた発言のみ記載してください。
背景雑音・機械音・環境音の記載は一切不要です。`,
        silenceThresholdDb: -35,
        silenceMinDuration: 3,
        label: '対面録音',
        icon: 'users',
      };

    default:
      return {
        transcriptPrompt: `この音声を正確に文字起こししてください。
話者が区別できる場合は分けてください。
聞き取れない箇所は無視して、聞き取れた発言のみ記載してください。
背景雑音・ノイズの記載は不要です。`,
        silenceThresholdDb: -30,
        silenceMinDuration: 3,
        label: '自動判別',
        icon: 'mic',
      };
  }
}
