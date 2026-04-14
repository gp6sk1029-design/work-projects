import type { Smc2Project } from './smc2Parser';

export interface CrossCheckResult {
  plcVariablesUsedInHmi: number;
  plcVariablesNotInHmi: number;
  hmiVariablesNotInPlc: number;
  unmatchedTypes: number;
  details: {
    missingInPlc: string[];
    unusedInHmi: string[];
    typeMismatches: { variable: string; plcType: string; hmiExpected: string }[];
  };
}

export interface AlarmCoverageResult {
  plcErrorFlags: number;
  hmiAlarmsDefined: number;
  uncoveredErrors: string[];
}

// PLCとHMI間の変数クロスリファレンスチェック
export function checkCrossReference(project: Smc2Project): CrossCheckResult {
  const plcVarNames = new Set(project.variables.map((v) => v.name));
  const hmiVarNames = new Set<string>();

  // HMI画面から参照されている変数を収集
  for (const screen of project.hmi.screens) {
    for (const el of screen.elements) {
      if (el.variable) hmiVarNames.add(el.variable);
      if (el.action?.targetVariable) hmiVarNames.add(el.action.targetVariable);
    }
  }

  const usedInHmi = project.variables.filter((v) => v.usedInHmi).length;
  const notInHmi = project.variables.filter((v) => !v.usedInHmi).length;

  // HMI側で参照されているがPLCに存在しない変数
  const missingInPlc = Array.from(hmiVarNames).filter((v) => !plcVarNames.has(v));

  // PLC変数でHMI未使用のもの（ただしシステム変数は除外）
  const unusedInHmi = project.variables
    .filter((v) => !v.usedInHmi && !v.name.startsWith('_') && v.scope === 'global')
    .map((v) => v.name);

  return {
    plcVariablesUsedInHmi: usedInHmi,
    plcVariablesNotInHmi: notInHmi,
    hmiVariablesNotInPlc: missingInPlc.length,
    unmatchedTypes: 0, // TODO: 型チェックの実装
    details: {
      missingInPlc,
      unusedInHmi,
      typeMismatches: [],
    },
  };
}

// アラームカバレッジチェック
export function checkAlarmCoverage(project: Smc2Project): AlarmCoverageResult {
  // エラー関連のPLC変数を検出（命名規則ベース）
  const errorPatterns = [/err/i, /error/i, /alarm/i, /fault/i, /warn/i, /EMS/i, /Min_Error/i];

  const plcErrorFlags = project.variables.filter((v) =>
    errorPatterns.some((p) => p.test(v.name)) && v.dataType === 'BOOL',
  );

  const hmiAlarmVars = new Set(project.hmi.alarms.map((a) => a.plcVariable));

  const uncoveredErrors = plcErrorFlags
    .filter((v) => !hmiAlarmVars.has(v.name))
    .map((v) => v.name);

  return {
    plcErrorFlags: plcErrorFlags.length,
    hmiAlarmsDefined: project.hmi.alarms.length,
    uncoveredErrors,
  };
}
