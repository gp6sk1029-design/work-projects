import Anthropic from '@anthropic-ai/sdk';

export interface HmiScreenshotAnalysis {
  screenName: string;
  detectedElements: {
    type: string;
    label: string;
    position: string;
    state?: string;
  }[];
  layoutIssues: string[];
  uxIssues: string[];
  safetyIssues: string[];
}

const HMI_ANALYSIS_PROMPT = `あなたはHMI画面設計の専門家です。
提供されたHMI画面のスクリーンショットを分析し、以下の観点で問題を検出してください。

【分析観点】
1. レイアウトと視認性（文字サイズ、コントラスト、配色、情報密度）
2. 操作安全性（危険操作ボタンの位置、非常停止表示、ボタンサイズ・間隔）
3. 状態表示の明確さ（運転状態表示、数値単位、ランプ表現）
4. 一般的なUXの問題（ナビゲーション、戻るボタン、表記統一性）

結果は以下のJSON形式で出力してください:
{
  "screenName": "推定画面名",
  "detectedElements": [{"type": "要素タイプ", "label": "表示テキスト", "position": "位置", "state": "状態"}],
  "layoutIssues": ["問題1"],
  "uxIssues": ["問題1"],
  "safetyIssues": ["問題1"]
}

JSONのみ出力してください。`;

export async function analyzeHmiScreenshot(
  client: Anthropic,
  imageBase64: string,
  mediaType: 'image/png' | 'image/jpeg',
): Promise<HmiScreenshotAnalysis> {
  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 4096,
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'image',
            source: { type: 'base64', media_type: mediaType, data: imageBase64 },
          },
          { type: 'text', text: HMI_ANALYSIS_PROMPT },
        ],
      },
    ],
  });

  const text = response.content.find((c) => c.type === 'text')?.text || '{}';

  try {
    // JSONブロックを抽出
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }
  } catch {
    console.error('Vision API レスポンスのJSONパース失敗');
  }

  return {
    screenName: '不明',
    detectedElements: [],
    layoutIssues: [],
    uxIssues: ['Vision API レスポンスの解析に失敗しました'],
    safetyIssues: [],
  };
}
