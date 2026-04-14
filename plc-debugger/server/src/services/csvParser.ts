import Papa from 'papaparse';
import type { PlcVariable } from './smc2Parser';

// Sysmac Studio変数テーブルCSVのヘッダーパターン
const HEADER_PATTERNS = {
  name: ['名前', 'Name', '変数名'],
  dataType: ['データ型', 'DataType', 'Data Type', 'Type'],
  address: ['AT指定', 'Address', 'AT', 'AT Specification'],
  initialValue: ['初期値', 'Initial Value', 'InitialValue'],
  retained: ['保持', 'Retained', 'Retain'],
  comment: ['コメント', 'Comment'],
  network: ['ネットワーク公開', 'Network Publish', 'NetworkPublication'],
};

function findColumnIndex(headers: string[], patterns: string[]): number {
  for (const pattern of patterns) {
    const idx = headers.findIndex((h) => h.trim().toLowerCase() === pattern.toLowerCase());
    if (idx !== -1) return idx;
  }
  return -1;
}

export function parseCsvVariables(csvContent: string): PlcVariable[] {
  const result = Papa.parse(csvContent, {
    skipEmptyLines: true,
  });

  if (!result.data || result.data.length < 2) return [];

  const rows = result.data as string[][];

  // ヘッダー行を検出（最初の3行以内で探す）
  let headerRow = -1;
  let columnMap: Record<string, number> = {};

  for (let i = 0; i < Math.min(3, rows.length); i++) {
    const row = rows[i];
    const nameIdx = findColumnIndex(row, HEADER_PATTERNS.name);
    const typeIdx = findColumnIndex(row, HEADER_PATTERNS.dataType);

    if (nameIdx !== -1 && typeIdx !== -1) {
      headerRow = i;
      columnMap = {
        name: nameIdx,
        dataType: typeIdx,
        address: findColumnIndex(row, HEADER_PATTERNS.address),
        initialValue: findColumnIndex(row, HEADER_PATTERNS.initialValue),
        comment: findColumnIndex(row, HEADER_PATTERNS.comment),
      };
      break;
    }
  }

  if (headerRow === -1) return [];

  const variables: PlcVariable[] = [];

  for (let i = headerRow + 1; i < rows.length; i++) {
    const row = rows[i];
    const name = row[columnMap.name]?.trim();
    if (!name) continue;

    variables.push({
      name,
      dataType: row[columnMap.dataType]?.trim() || 'UNKNOWN',
      scope: 'global',
      initialValue: columnMap.initialValue >= 0 ? row[columnMap.initialValue]?.trim() : undefined,
      comment: columnMap.comment >= 0 ? row[columnMap.comment]?.trim() : undefined,
      address: columnMap.address >= 0 ? row[columnMap.address]?.trim() : undefined,
      usedInHmi: false,
    });
  }

  return variables;
}

// ログCSVの判別と解析
export function parseCsvLog(csvContent: string): { type: 'variables' | 'log'; data: any } {
  const result = Papa.parse(csvContent, { skipEmptyLines: true });
  const rows = result.data as string[][];

  if (rows.length < 2) return { type: 'log', data: [] };

  const headers = rows[0];
  const hasVarHeaders = findColumnIndex(headers, HEADER_PATTERNS.name) !== -1 &&
    findColumnIndex(headers, HEADER_PATTERNS.dataType) !== -1;

  if (hasVarHeaders) {
    return { type: 'variables', data: parseCsvVariables(csvContent) };
  }

  return { type: 'log', data: rows };
}
