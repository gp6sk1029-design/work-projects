import { GoogleAIFileManager, FileState } from '@google/generative-ai/server';
import { GoogleGenerativeAI } from '@google/generative-ai';
import fs from 'fs';
import path from 'path';
import type { AudioMode, SummaryType, TranscriptSegment } from '../types';
import { getModeParams } from './audioAnalyzer';

const apiKey = process.env.GEMINI_API_KEY || '';
const genAI = new GoogleGenerativeAI(apiKey);
const fileManager = new GoogleAIFileManager(apiKey);

const MODEL_NAME = 'gemini-2.5-flash';

// Gemini File APIでファイルアップロード
export async function uploadToGemini(
  filePath: string,
  mimeType: string,
  onProgress?: (message: string) => void,
): Promise<string> {
  onProgress?.('Gemini File APIにアップロード中...');

  const uploadResult = await fileManager.uploadFile(filePath, {
    mimeType,
    displayName: path.basename(filePath),
  });

  // 処理完了待ち
  let file = uploadResult.file;
  while (file.state === FileState.PROCESSING) {
    onProgress?.(`ファイル処理中... (${file.name})`);
    await new Promise(resolve => setTimeout(resolve, 3000));
    file = await fileManager.getFile(file.name);
  }

  if (file.state === FileState.FAILED) {
    throw new Error('Geminiファイル処理に失敗しました');
  }

  onProgress?.('アップロード完了');
  return file.uri;
}

// 文字起こし
export async function transcribe(
  fileUri: string,
  mimeType: string,
  audioMode: AudioMode,
  isVideo: boolean,
): Promise<{ fullText: string; segments: TranscriptSegment[] }> {
  const modeParams = getModeParams(audioMode);
  const model = genAI.getGenerativeModel({ model: MODEL_NAME });

  const videoInstructions = isVideo
    ? `\n\n動画内に表示されているテキスト（スライド、ホワイトボード、画面共有の内容など）も認識し、
文字起こしの該当箇所に [画面テキスト: "内容"] の形式で挿入してください。`
    : '';

  const prompt = `${modeParams.transcriptPrompt}${videoInstructions}

重要なルール:
- 人の発言のみを文字起こしすること
- 背景雑音、機械音、環境音は一切記載しないこと（[背景雑音]や[聞き取り不明]などのタグも不要）
- 聞き取れない箇所は無視して、聞き取れた発言だけを記載すること
- 無音区間やノイズだけの区間はスキップすること

以下のJSON形式で出力してください。コードブロック(\`\`\`)で囲まないでください:
{"fullText":"文字起こし全文","segments":[{"start":0.0,"end":10.5,"speaker":"話者A","text":"発言テキスト"}]}

注意:
- start/endは秒数（小数点あり）
- 発言ごとにセグメントを分割
- 発言がない区間はセグメントを作らない`;

  const result = await model.generateContent([
    { text: prompt },
    {
      fileData: {
        mimeType,
        fileUri,
      },
    },
  ]);

  const text = result.response.text();
  try {
    // コードブロックやマークダウン記法を除去
    let jsonStr = text
      .replace(/```json\s*/g, '')
      .replace(/```\s*/g, '')
      .trim();

    // JSONの開始位置を探す（先頭にゴミテキストがある場合）
    const jsonStart = jsonStr.indexOf('{');
    const jsonEnd = jsonStr.lastIndexOf('}');
    if (jsonStart >= 0 && jsonEnd > jsonStart) {
      jsonStr = jsonStr.substring(jsonStart, jsonEnd + 1);
    }

    const parsed = JSON.parse(jsonStr);

    // [背景雑音]等のノイズタグを含むセグメントをフィルタ
    if (parsed.segments && Array.isArray(parsed.segments)) {
      parsed.segments = parsed.segments.filter((seg: any) => {
        const t = (seg.text || '').trim();
        // ノイズタグのみのセグメントを除外
        if (/^\[.*\]$/.test(t)) return false;
        if (t.length === 0) return false;
        return true;
      });
      // fullTextもクリーンアップ
      parsed.fullText = parsed.segments.map((s: any) => s.text).join('\n');
    }

    return parsed;
  } catch (e) {
    console.error('JSON解析エラー、プレーンテキストとして処理:', e);
    // ノイズタグを除去してプレーンテキストとして返す
    const cleanText = text
      .replace(/```json\s*/g, '').replace(/```\s*/g, '')
      .replace(/\[背景雑音[^\]]*\]/g, '')
      .replace(/\[聞き取り不明[^\]]*\]/g, '')
      .replace(/\[.*?作動音[^\]]*\]/g, '')
      .replace(/\[.*?雑音[^\]]*\]/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    return {
      fullText: cleanText,
      segments: [{ start: 0, end: 0, text: cleanText }],
    };
  }
}

// 要約生成
export async function summarize(
  text: string,
  type: SummaryType,
): Promise<string> {
  const model = genAI.getGenerativeModel({ model: MODEL_NAME });

  const prompts: Record<SummaryType, string> = {
    brief: `以下の文字起こしテキストを、3〜5行で簡潔に要約してください。
重要なポイントのみを抽出し、箇条書きで記載してください。

文字起こし:
${text}`,

    detailed: `以下の文字起こしテキストを、詳細に要約してください。
議論の流れ、各話者の主張、結論を含めてください。
セクションごとに見出しをつけて構造化してください。

文字起こし:
${text}`,

    minutes: `以下の文字起こしテキストから、会議議事録を作成してください。

以下の形式で出力してください:
## 会議議事録
- **日時**: （推定できれば記載）
- **参加者**: （話者名）
- **議題**:

### 議論内容
（議論の流れを時系列で記載）

### 決定事項
（決まったこと）

### 懸念事項・課題
（未解決の問題）

文字起こし:
${text}`,

    action_items: `以下の文字起こしテキストから、アクションアイテム（ToDo）を抽出してください。

以下の形式で出力してください:
## アクションアイテム

| 優先度 | 担当者 | タスク内容 | 期限 |
|--------|--------|-----------|------|
| 高/中/低 | 話者名 | 具体的なタスク | 推定期限 |

### 補足情報
（各タスクの背景や詳細）

文字起こし:
${text}`,
  };

  const result = await model.generateContent(prompts[type]);
  return result.response.text();
}

// チャットQ&A
export async function chat(
  message: string,
  transcriptText: string,
  history: { role: 'user' | 'model'; parts: { text: string }[] }[],
): Promise<string> {
  const model = genAI.getGenerativeModel({ model: MODEL_NAME });

  const chatSession = model.startChat({
    history: [
      {
        role: 'user',
        parts: [{ text: `以下は音声/動画の文字起こしテキストです。この内容について質問に回答してください。\n\n---\n${transcriptText}\n---` }],
      },
      {
        role: 'model',
        parts: [{ text: 'はい、文字起こしの内容を確認しました。ご質問をどうぞ。' }],
      },
      ...history,
    ],
  });

  const result = await chatSession.sendMessage(message);
  return result.response.text();
}

// マインドマップ生成
export async function generateMindmap(
  text: string,
  title?: string,
): Promise<string> {
  const model = genAI.getGenerativeModel({ model: MODEL_NAME });

  const prompt = `以下のテキストの論理構造をMermaid.jsのマインドマップ形式で表現してください。

ルール:
- Mermaid mindmap構文を使用してください
- ルートノードは「${title || '会議内容'}」としてください
- 主要トピック、サブトピック、具体的な項目の3階層程度にしてください
- 日本語で記載してください
- コードブロック(\`\`\`)は含めず、Mermaid構文のみ出力してください

テキスト:
${text}`;

  const result = await model.generateContent(prompt);
  const mermaidCode = result.response.text().replace(/```mermaid\n?/g, '').replace(/```\n?/g, '').trim();
  return mermaidCode;
}

// セクション分割提案
export async function suggestSections(
  transcriptText: string,
  silences: { start: number; end: number }[],
  durationSeconds: number,
): Promise<{ title: string; start_time: number; end_time: number; summary: string }[]> {
  const model = genAI.getGenerativeModel({ model: MODEL_NAME });

  const prompt = `以下の文字起こしテキストを意味的なセクションに分割してください。

無音区間（話題の切れ目の候補）:
${JSON.stringify(silences.map(s => ({ start: Math.round(s.start), end: Math.round(s.end) })))}

全体の長さ: ${Math.round(durationSeconds)}秒

以下のJSON形式で出力してください。他のテキストは含めないでください:
[
  {
    "title": "セクションタイトル",
    "start_time": 0.0,
    "end_time": 120.0,
    "summary": "このセクションの1行要約"
  }
]

注意:
- 3〜10個程度のセクションに分割してください
- 無音区間を参考にしつつ、内容の変わり目で分割してください
- start_time/end_timeは秒数で、隙間なく全体をカバーしてください

文字起こし:
${transcriptText}`;

  const result = await model.generateContent(prompt);
  const text = result.response.text();
  try {
    const jsonStr = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    return JSON.parse(jsonStr);
  } catch {
    return [{
      title: '全体',
      start_time: 0,
      end_time: durationSeconds,
      summary: '自動分割できませんでした',
    }];
  }
}
