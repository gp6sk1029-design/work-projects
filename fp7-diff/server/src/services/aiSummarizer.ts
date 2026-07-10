/**
 * AI解説サマリ生成（Gemini 2.5 Flash）
 *  - 変数・コメント差分の要点を抽出し、「横展開・標準化・改造履歴」観点で解説
 *  - 大量データはAIに渡さず、追加/削除/変更のみをサンプリングして渡す
 */
import { GoogleGenerativeAI } from '@google/generative-ai';
import { safeParseGeminiJson } from './jsonRepair';
import type { DiffResult, DiffRow } from './diffCalculator';

const MODEL = 'gemini-2.5-flash';

const SYSTEM_PROMPT = `あなたはPanasonic FP7 (FPWIN GR7) PLCプログラムの差分解析専門家です。
生産設備の制御プログラム（油圧式バックアップ装置・プレス設備等）の横展開・標準化・改造履歴管理を支援します。

【解析方針】
1. 単なる差分列挙ではなく、「なぜこの変更があったか」を生産技術的に推論する
2. 機能追加（横展開）／命名変更（標準化）／削除（廃止/廃版）を区別する
3. デバイスカテゴリ（X物理入力／Y物理出力／R内部リレー／DTデータレジスタ／SDシステム等）の特性を踏まえる
4. 業務的に重要な変更を3〜5点に絞って「主要な変更ポイント」として強調する
5. 横展開時のリスク（互換性・既存ロジックへの影響）も指摘する

【出力】
必ず指定のJSON形式で出力。推測がある場合は明示。`;

export interface AiSummary {
  overview: string;
  mainChanges: { title: string; description: string; impact: string }[];
  patterns: { name: string; description: string; examples: string[] }[];
  risks: { description: string; severity: 'high' | 'medium' | 'low' }[];
  recommendations: string[];
}

export class AiSummarizer {
  private genAI: GoogleGenerativeAI;

  constructor(apiKey: string) {
    this.genAI = new GoogleGenerativeAI(apiKey);
  }

  async summarize(diff: DiffResult): Promise<AiSummary> {
    // サンプリング：差分があるものだけ、各カテゴリ最大10件まで
    const changed = diff.rows.filter((r) => r.status === 'changed').slice(0, 50);
    const added = diff.rows.filter((r) => r.status === 'added').slice(0, 50);
    const removed = diff.rows.filter((r) => r.status === 'removed').slice(0, 50);

    const formatRows = (rows: DiffRow[]) =>
      rows.map((r) => {
        if (r.status === 'changed') return `  ${r.address} (${r.category}): "${r.commentA}" → "${r.commentB}"`;
        if (r.status === 'added') return `  ${r.address} (${r.category}): "${r.commentB}"`;
        return `  ${r.address} (${r.category}): "${r.commentA}"`;
      }).join('\n');

    const model = this.genAI.getGenerativeModel({
      model: MODEL,
      systemInstruction: SYSTEM_PROMPT,
    });

    const prompt = `以下はPanasonic FP7 PLCプログラム2つの差分です。

【プロジェクトA】 ${diff.metadata.projectAName} (デバイス${diff.metadata.countA}個)
【プロジェクトB】 ${diff.metadata.projectBName} (デバイス${diff.metadata.countB}個)

## 差分サマリ
- 変更: ${diff.summary.byStatus.changed}件
- A→B追加: ${diff.summary.byStatus.added}件
- A→B削除: ${diff.summary.byStatus.removed}件
- 同一: ${diff.summary.byStatus.same}件

## カテゴリ別変更件数
${Object.entries(diff.summary.byCategory)
  .filter(([_, v]) => v.changed + v.added + v.removed > 0)
  .map(([cat, v]) => `  ${cat}: 変更${v.changed} 追加${v.added} 削除${v.removed}`)
  .join('\n')}

## 変更コメント（最大50件サンプル）
${formatRows(changed)}

## 追加コメント（最大50件サンプル）
${formatRows(added)}

## 削除コメント（最大50件サンプル）
${formatRows(removed)}

以下のJSON形式で出力してください:
{
  "overview": "全体所見（2-3文）",
  "mainChanges": [
    {"title": "変更ポイントの見出し", "description": "詳細", "impact": "業務への影響"}
  ],
  "patterns": [
    {"name": "パターン名（例: 「○○制御の追加」「命名規則変更」）", "description": "説明", "examples": ["DT3630", "DT3650"]}
  ],
  "risks": [
    {"description": "横展開時のリスク内容", "severity": "high|medium|low"}
  ],
  "recommendations": ["推奨アクション1", "推奨アクション2"]
}

JSONのみ出力してください。`;

    const result = await model.generateContent(prompt);
    const text = result.response.text();
    const parsed = safeParseGeminiJson(text, 'AI解説');

    if (parsed) {
      return {
        overview: parsed.overview || '',
        mainChanges: Array.isArray(parsed.mainChanges) ? parsed.mainChanges : [],
        patterns: Array.isArray(parsed.patterns) ? parsed.patterns : [],
        risks: Array.isArray(parsed.risks) ? parsed.risks : [],
        recommendations: Array.isArray(parsed.recommendations) ? parsed.recommendations : [],
      };
    }

    return {
      overview: 'AI解説の生成に失敗しました。差分テーブルをご確認ください。',
      mainChanges: [],
      patterns: [],
      risks: [],
      recommendations: [],
    };
  }
}
