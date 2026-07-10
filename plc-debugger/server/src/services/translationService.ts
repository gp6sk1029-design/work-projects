/**
 * 設備翻訳サービス（日⇄英 + 略語提案）
 * Gemini 2.5 Flash + 設備特化プロンプト
 */
import { GoogleGenerativeAI } from '@google/generative-ai';
import { listGlossary } from '../db/glossaryDb';
import { safeParseGeminiJson } from './jsonRepair';

const MODEL = 'gemini-2.5-flash';

export type TranslationDirection = 'ja-en' | 'en-ja' | 'auto';
export type TranslationMode = 'sentence' | 'variable' | 'abbr-lookup';

export interface AbbreviationCandidate {
  abbr: string;
  expansion: string;
  reason: string;
}

export interface VariableNameCandidate {
  name: string;
  style: string; // "IEC準拠 (b_xxx)" / "ハンガリアン" / "シンプル" 等
  reason: string;
}

export interface TranslationResult {
  translation: string;
  alternatives: string[];
  abbreviations: AbbreviationCandidate[];
  variableNames: VariableNameCandidate[];
  contextNote: string;
  detectedLanguage: 'ja' | 'en';
}

const SYSTEM_PROMPT = `あなたは生産設備（PLC・機械・電気制御・産業オートメーション）専門の翻訳エキスパートです。
オムロン Sysmac Studio、三菱 GX Works、シーメンス TIA Portal などの主要PLCベンダーに精通し、
自動車・半導体・食品・医薬品業界の生産設備の現場で使われる用語を熟知しています。

【翻訳ルール】
- 一般的な翻訳ではなく、生産設備・制御の文脈に固定された訳を最優先
- 例：「主軸」→ "main spindle"（musical instrumentの軸ではない）
- 例：「リセット」→ "reset"（PLC文脈では fault reset / system reset を区別）
- 例：「インターロック」は カタカナ英語ではなく "interlock" として扱う
- 例：「自働化」と「自動化」は違う（前者=Jidoka、後者=Automation）
- 業界用語は意訳ではなく業界標準訳を選ぶ

【略語提案ルール（PLC変数名・図面表記向け）】
- 国際的に通用する略語を最優先（例：EMG, EStop, MTR, SOL, SV, INV, PB, LS, PS, FS, TC, SSR）
- IEC 61131-3 命名規則を尊重（プレフィックス: b_=BOOL, i_=INT, r_=REAL 等）
- 略語が複数候補ある場合は、業界での頻度順に並べる
- 略語の根拠（元の英単語）を必ず示す

【変数名候補ルール】
- 3スタイル提案する：
  1. IEC 61131-3 準拠（b_/i_/r_ プレフィックス）
  2. ハンガリアン記法（x=BOOL, n=INT, f=REAL）
  3. シンプルキャメル（EmgStop, MainMotor）
- 各候補に「なぜこの命名か」の理由を添える

【出力】
- 必ず指定のJSON形式
- 推測がある場合は contextNote で明示
- 文脈不明な場合は最有力候補を1つ＋他候補を alternatives に並べる`;

export class TranslationService {
  private genAI: GoogleGenerativeAI;

  constructor(apiKey: string) {
    this.genAI = new GoogleGenerativeAI(apiKey);
  }

  /**
   * 翻訳実行
   */
  async translate(
    text: string,
    direction: TranslationDirection,
    mode: TranslationMode,
  ): Promise<TranslationResult> {
    // 社内用語辞書を取得（hit_count上位30件のみAIに渡す）
    const glossary = await listGlossary();
    const glossaryHints = glossary.slice(0, 30).map((g) => ({
      ja: g.term_ja,
      en: g.term_en,
      abbr: g.abbr,
      note: g.note,
    }));

    const model = this.genAI.getGenerativeModel({
      model: MODEL,
      systemInstruction: SYSTEM_PROMPT,
    });

    const directionHint =
      direction === 'auto'
        ? '入力テキストの言語を自動判定し、もう一方の言語に翻訳してください。'
        : direction === 'ja-en'
          ? '日本語 → 英語に翻訳してください。'
          : '英語 → 日本語に翻訳してください。';

    const modeHint =
      mode === 'sentence'
        ? '入力は文章・フレーズです。自然で正確な訳を1つ提示し、別案を2つ alternatives に入れてください。'
        : mode === 'variable'
          ? '入力はPLC変数名・信号名にしたい用語です。3スタイル（IEC/ハンガリアン/シンプル）の variableNames を出力してください。略語候補も abbreviations に充実させてください。'
          : '入力は略語の逆引き要求です。考えられる元の英単語/日本語を abbreviations に複数候補挙げ、最有力をtranslationに、文脈質問が必要なら contextNote に書いてください。';

    const glossarySection =
      glossaryHints.length > 0
        ? `\n\n【社内用語辞書（必ず優先採用）】\n${JSON.stringify(glossaryHints, null, 2)}`
        : '';

    const prompt = `【入力テキスト】
${text}

【翻訳方向】
${directionHint}

【モード】
${modeHint}
${glossarySection}

以下のJSON形式で出力してください（フィールドが該当なしの場合は空配列[]または空文字""で）:
{
  "translation": "主翻訳結果",
  "alternatives": ["別表現1", "別表現2"],
  "abbreviations": [
    {"abbr": "EMG", "expansion": "Emergency", "reason": "ISO規格・PLC業界標準"}
  ],
  "variableNames": [
    {"name": "b_xEStop", "style": "IEC 61131-3準拠 (b_=BOOL, x=非常停止)", "reason": "国際規格"}
  ],
  "contextNote": "文脈に関する補足（推測の根拠・別解釈の可能性等）",
  "detectedLanguage": "ja"
}

JSONのみ出力してください。`;

    const result = await model.generateContent(prompt);
    const responseText = result.response.text();

    const parsed = safeParseGeminiJson(responseText, '翻訳');
    if (parsed) {
      return {
        translation: parsed.translation || '',
        alternatives: Array.isArray(parsed.alternatives) ? parsed.alternatives : [],
        abbreviations: Array.isArray(parsed.abbreviations) ? parsed.abbreviations : [],
        variableNames: Array.isArray(parsed.variableNames) ? parsed.variableNames : [],
        contextNote: parsed.contextNote || '',
        detectedLanguage: parsed.detectedLanguage === 'en' ? 'en' : 'ja',
      };
    }

    // フォールバック
    return {
      translation: responseText.trim() || '翻訳に失敗しました。',
      alternatives: [],
      abbreviations: [],
      variableNames: [],
      contextNote: 'AIレスポンスの解析に失敗。生テキストを返却。',
      detectedLanguage: 'ja',
    };
  }
}
