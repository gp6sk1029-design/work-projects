import type { PlcProgram, PlcVariable } from './smc2Parser';

export interface StParseResult {
  programs: PlcProgram[];
  variables: PlcVariable[];
}

export function parseStText(content: string, fileName: string): StParseResult {
  const programs: PlcProgram[] = [];
  const variables: PlcVariable[] = [];

  // PROGRAM...END_PROGRAM ブロックの抽出
  const programPattern = /PROGRAM\s+(\w+)([\s\S]*?)END_PROGRAM/gi;
  let match;

  while ((match = programPattern.exec(content)) !== null) {
    const programName = match[1];
    const programBody = match[2];

    programs.push({
      name: programName,
      language: 'ST',
      source: match[0],
      taskAssignment: '',
    });

    // VAR...END_VAR ブロックから変数を抽出
    const varPattern = /VAR(?:_(?:GLOBAL|INPUT|OUTPUT|IN_OUT))?\s*([\s\S]*?)END_VAR/gi;
    let varMatch;
    while ((varMatch = varPattern.exec(programBody)) !== null) {
      const varBlock = varMatch[1];
      const varLines = varBlock.split('\n');

      for (const line of varLines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('//') || trimmed.startsWith('(*')) continue;

        // パターン: varName : DataType := initialValue; // comment
        const varDef = trimmed.match(/^(\w+)\s*:\s*(\w[\w\[\](),.]*)\s*(?::=\s*([^;]+))?\s*;?\s*(?:\/\/\s*(.*))?$/);
        if (varDef) {
          variables.push({
            name: varDef[1],
            dataType: varDef[2],
            scope: 'local',
            initialValue: varDef[3]?.trim(),
            comment: varDef[4]?.trim(),
            usedInHmi: false,
          });
        }
      }
    }
  }

  // PROGRAM ブロックが見つからない場合は全体を1つのプログラムとして扱う
  if (programs.length === 0) {
    programs.push({
      name: fileName.replace(/\.(st|txt)$/i, ''),
      language: 'ST',
      source: content,
      taskAssignment: '',
    });
  }

  return { programs, variables };
}
