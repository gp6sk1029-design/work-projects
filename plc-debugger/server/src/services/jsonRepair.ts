/**
 * Geminiレスポンス用 頑健なJSONパーサ（3段階リトライ）
 *
 * Geminiは説明文に生の改行・制御文字・不正バックスラッシュを混入させることが
 * あり、標準のJSON.parseでは失敗する。本ヘルパーは段階的に修復を試みる。
 *
 *  1. ```json ラッパー除去 → 不正バックスラッシュエスケープ修復 → パース
 *  2. 文字列値内の生改行・タブ・制御文字をエスケープしてパース
 *  3. 文字列値内のあらゆる単独バックスラッシュをダブル化してパース
 *
 * @param text Geminiレスポンス本文
 * @param label デバッグ用ラベル（ログに表示）
 * @returns パース成功時はオブジェクト、失敗時はnull
 */
export function safeParseGeminiJson(text: string, label: string): any {
  const cleaned = text.replace(/^```json\s*/i, '').replace(/\s*```\s*$/i, '');
  const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    console.error(`[${label}] JSON抽出失敗 - レスポンス先頭500文字:`, text.substring(0, 500));
    return null;
  }
  const raw = jsonMatch[0];

  // === 試行1: 一般的な不正エスケープ修復 ===
  try {
    const fixed = raw.replace(/\\([^"\\\/bfnrtu])/g, '\\\\$1');
    return JSON.parse(fixed);
  } catch (err1) {
    console.warn(`[${label}] パース試行1失敗:`, (err1 as Error).message);
  }

  // === 試行2: 文字列値内の生改行・制御文字をエスケープ ===
  try {
    const fixed = repairJsonStrings(raw);
    return JSON.parse(fixed);
  } catch (err2) {
    console.warn(`[${label}] パース試行2失敗:`, (err2 as Error).message);
  }

  // === 試行3: あらゆる不正バックスラッシュをダブル化 ===
  try {
    let fixed = repairJsonStrings(raw);
    fixed = fixed.replace(/\\(?!["\\\/bfnrtu])/g, '\\\\');
    return JSON.parse(fixed);
  } catch (err3) {
    console.error(`[${label}] パース全試行失敗:`, (err3 as Error).message);
    console.error(`[${label}] レスポンス先頭500文字:`, raw.substring(0, 500));
    return null;
  }
}

/**
 * JSON文字列値内の生改行・制御文字をエスケープ
 * （AIが説明文に生の改行・タブを入れた場合の対策）
 */
function repairJsonStrings(raw: string): string {
  let result = '';
  let inString = false;
  let escaped = false;
  for (let i = 0; i < raw.length; i++) {
    const ch = raw[i];
    if (escaped) {
      result += ch;
      escaped = false;
      continue;
    }
    if (ch === '\\') {
      result += ch;
      escaped = true;
      continue;
    }
    if (ch === '"') {
      inString = !inString;
      result += ch;
      continue;
    }
    if (inString) {
      if (ch === '\n') result += '\\n';
      else if (ch === '\r') result += '\\r';
      else if (ch === '\t') result += '\\t';
      else if (ch.charCodeAt(0) < 0x20) result += `\\u${ch.charCodeAt(0).toString(16).padStart(4, '0')}`;
      else result += ch;
    } else {
      result += ch;
    }
  }
  return result;
}
