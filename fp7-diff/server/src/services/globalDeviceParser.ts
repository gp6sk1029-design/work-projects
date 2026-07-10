/**
 * FPWIN GR7 グローバルデバイス.txt パーサ
 * - エンコーディング: UTF-16 LE BOM付き（FPWIN GR7標準出力）
 * - フォーマット: タブ区切り `アドレス\tコメント\t属性1\t属性2`
 * - 一行例: `X100\tタイミング入力1\t\t`
 */
import * as fs from 'fs';

export interface DeviceEntry {
  address: string;       // 例: X100, R220, DT510, SD65
  comment: string;       // 日本語コメント
  category: DeviceCategory;
  raw: string;           // 元の行（デバッグ用）
}

export type DeviceCategory =
  | 'X'   // 物理入力
  | 'Y'   // 物理出力
  | 'R'   // 内部リレー
  | 'L'   // リンクリレー
  | 'T'   // タイマー
  | 'C'   // カウンタ
  | 'DT'  // データレジスタ
  | 'LD'  // リンクデータレジスタ
  | 'SD'  // システムデータレジスタ
  | 'SR'  // システムリレー
  | 'FL'  // ファイルレジスタ
  | 'P'   // ラベル/ポインタ
  | 'WX'  // ワード入力
  | 'WY'  // ワード出力
  | 'WR'  // ワードリレー
  | 'OTHER';

/**
 * デバイスアドレスからカテゴリを判定
 * （長い接頭辞を先に判定するためソート済みリストを使う）
 */
const PREFIXES: { prefix: string; category: DeviceCategory }[] = [
  { prefix: 'DT', category: 'DT' },
  { prefix: 'LD', category: 'LD' },
  { prefix: 'SD', category: 'SD' },
  { prefix: 'SR', category: 'SR' },
  { prefix: 'FL', category: 'FL' },
  { prefix: 'WX', category: 'WX' },
  { prefix: 'WY', category: 'WY' },
  { prefix: 'WR', category: 'WR' },
  { prefix: 'X', category: 'X' },
  { prefix: 'Y', category: 'Y' },
  { prefix: 'R', category: 'R' },
  { prefix: 'L', category: 'L' },
  { prefix: 'T', category: 'T' },
  { prefix: 'C', category: 'C' },
  { prefix: 'P', category: 'P' },
];

export function categorizeAddress(address: string): DeviceCategory {
  for (const { prefix, category } of PREFIXES) {
    if (address.startsWith(prefix)) return category;
  }
  return 'OTHER';
}

/**
 * ファイルバッファを読み取り、エンコーディング自動判定でデコード
 */
export function decodeBuffer(buf: Buffer): string {
  if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) {
    // UTF-16 LE BOM付き
    return buf.slice(2).toString('utf16le');
  }
  if (buf.length >= 2 && buf[0] === 0xfe && buf[1] === 0xff) {
    // UTF-16 BE BOM付き → swap then decode
    const swapped = Buffer.alloc(buf.length - 2);
    for (let i = 2; i < buf.length; i += 2) {
      swapped[i - 2] = buf[i + 1];
      swapped[i - 2 + 1] = buf[i];
    }
    return swapped.toString('utf16le');
  }
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    return buf.slice(3).toString('utf8');
  }
  // FPWIN GR7はデフォルトでUTF-16 LE BOMなしの可能性も
  // ヒューリスティック：奇数バイトが多数0なら UTF-16 LE
  let zeroOdd = 0;
  const sample = Math.min(buf.length, 200);
  for (let i = 1; i < sample; i += 2) if (buf[i] === 0) zeroOdd++;
  if (zeroOdd > sample / 4) {
    return buf.toString('utf16le');
  }
  // フォールバック: Shift_JIS（CP932）扱いを試みる
  try {
    // Node標準ではCP932デコード不可。UTF-8で試行
    return buf.toString('utf8');
  } catch {
    return buf.toString('latin1');
  }
}

/**
 * パース本体
 */
export function parseGlobalDeviceFile(filepath: string): DeviceEntry[] {
  const buf = fs.readFileSync(filepath);
  return parseGlobalDeviceText(decodeBuffer(buf));
}

export function parseGlobalDeviceText(text: string): DeviceEntry[] {
  // BOM残骸除去
  text = text.replace(/^﻿/, '');
  const lines = text.split(/\r?\n/);
  const entries: DeviceEntry[] = [];
  for (const line of lines) {
    if (!line.trim()) continue;
    const cols = line.split('\t');
    const address = cols[0]?.trim() || '';
    if (!address) continue;
    // アドレスは英大文字始まり＋英数字
    if (!/^[A-Z][A-Z0-9]*$/i.test(address)) continue;
    const comment = (cols[1] || '').trim();
    entries.push({
      address,
      comment,
      category: categorizeAddress(address),
      raw: line,
    });
  }
  return entries;
}
