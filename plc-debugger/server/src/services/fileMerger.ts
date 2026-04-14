import type { Smc2Project, PlcVariable, PlcProgram } from './smc2Parser';

// 複数ソースからのデータを統合
export function mergeProjectData(
  smc2Project: Smc2Project | null,
  csvVariables: PlcVariable[],
  stPrograms: { programs: PlcProgram[]; variables: PlcVariable[] } | null,
  pdfText: string | null,
): Smc2Project {
  // ベースプロジェクト（.smc2があればそれ、なければ空）
  const base: Smc2Project = smc2Project || {
    projectInfo: { name: 'Unnamed Project', controller: 'Unknown', version: '', hasHmi: false },
    programs: [],
    variables: [],
    tasks: [],
    axes: [],
    ethercat: { slaves: [] },
    io: [],
    hmi: {
      screens: [],
      alarms: [],
      dataLogs: [],
      globalObjects: [],
      screenTransitions: [],
      userAccounts: [],
    },
  };

  // CSVの変数をマージ（.smc2の変数を正とする）
  if (csvVariables.length > 0) {
    const existingNames = new Set(base.variables.map((v) => v.name));
    for (const v of csvVariables) {
      if (!existingNames.has(v.name)) {
        base.variables.push(v);
        existingNames.add(v.name);
      }
    }
  }

  // STプログラムをマージ
  if (stPrograms) {
    const existingPrograms = new Set(base.programs.map((p) => p.name));
    for (const p of stPrograms.programs) {
      if (!existingPrograms.has(p.name)) {
        base.programs.push(p);
        existingPrograms.add(p.name);
      }
    }

    const existingVars = new Set(base.variables.map((v) => v.name));
    for (const v of stPrograms.variables) {
      if (!existingVars.has(v.name)) {
        base.variables.push(v);
        existingVars.add(v.name);
      }
    }
  }

  // PDFテキスト（ST言語として解析を試みる）
  if (pdfText) {
    // PDFからの情報は信頼度が低いため、プログラム名に[PDF]を付与
    const pdfProgram = {
      name: '[PDF] extracted',
      language: 'ST' as const,
      source: pdfText,
      taskAssignment: '',
    };
    const existingPrograms = new Set(base.programs.map((p) => p.name));
    if (!existingPrograms.has(pdfProgram.name)) {
      base.programs.push(pdfProgram);
    }
  }

  return base;
}
