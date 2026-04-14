// === プロジェクト全体 ===
export interface Smc2Project {
  projectInfo: {
    name: string;
    controller: string;
    version: string;
    hasHmi: boolean;
  };
  programs: PlcProgram[];
  variables: PlcVariable[];
  tasks: PlcTask[];
  axes: PlcAxis[];
  ethercat: { slaves: EthercatSlave[] };
  io: PlcIO[];
  hmi: {
    screens: HmiScreen[];
    alarms: HmiAlarm[];
    dataLogs: HmiDataLog[];
    globalObjects: HmiGlobalObject[];
    screenTransitions: HmiScreenTransition[];
    userAccounts: HmiUserAccount[];
  };
}

export interface PlcProgram {
  name: string;
  language: 'ST' | 'LD' | 'FB';
  source: string;
  taskAssignment: string;
}

export interface PlcVariable {
  name: string;
  dataType: string;
  scope: 'global' | 'local';
  initialValue?: string;
  comment?: string;
  address?: string;
  usedInHmi: boolean;
}

export interface PlcTask {
  name: string;
  type: 'cyclic' | 'event' | 'interrupt';
  period?: string;
  priority: number;
}

export interface PlcAxis {
  name: string;
  axisNumber: number;
  mcGroup: string;
}

export interface EthercatSlave {
  name: string;
  vendor: string;
  nodeAddress: number;
}

export interface PlcIO {
  name: string;
  address: string;
  direction: 'input' | 'output';
  dataType: string;
}

// === HMI ===
export interface HmiScreen {
  id: string;
  name: string;
  screenNumber: number;
  elements: HmiElement[];
  scripts?: string[];
  openEvent?: string;
  closeEvent?: string;
}

export interface HmiElement {
  type: string;
  id: string;
  name?: string;
  variable?: string;
  readVariable?: string;
  writeVariable?: string;
  action?: {
    type: string;
    targetVariable?: string;
    targetScreen?: string;
    value?: string;
    script?: string;
  };
  conditions?: { expression: string; color?: string; blink?: boolean }[];
  format?: string;
  scalingMin?: number;
  scalingMax?: number;
  unit?: string;
  inputMin?: number;
  inputMax?: number;
  securityLevel?: number;
  position: { x: number; y: number; width: number; height: number };
  visible?: string;
}

export interface HmiAlarm {
  id: string;
  group: string;
  message: string;
  condition: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  acknowledgeRequired: boolean;
  autoReset: boolean;
  plcVariable: string;
}

export interface HmiDataLog {
  name: string;
  variables: string[];
  samplingInterval: number;
  storageType: string;
}

export interface HmiScreenTransition {
  fromScreen: string;
  toScreen: string;
  trigger: string;
  condition?: string;
}

export interface HmiGlobalObject {
  name: string;
  type: string;
  elements: HmiElement[];
}

export interface HmiUserAccount {
  level: number;
  name: string;
  description: string;
}

// === 分析結果 ===
export interface AnalysisResult {
  projectSummary: {
    controller: string;
    programCount: number;
    variableCount: number;
    axisCount: number;
    taskCount: number;
    hmiScreenCount: number;
    hmiAlarmCount: number;
    sourceTypes: string[];
    analysisConfidence: 'high' | 'medium' | 'low';
  };
  issues: AnalysisIssue[];
  hmiAnalysis?: {
    screenTransitionDiagram: string;
    crossReference: {
      plcVariablesUsedInHmi: number;
      plcVariablesNotInHmi: number;
      hmiVariablesNotInPlc: number;
      unmatchedTypes: number;
    };
    alarmCoverage: {
      plcErrorFlags: number;
      hmiAlarmsDefined: number;
      uncoveredErrors: string[];
    };
  };
  statistics: {
    critical: number;
    warning: number;
    info: number;
    byDomain: Record<string, { critical: number; warning: number; info: number }>;
  };
}

export interface AnalysisIssue {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  category: string;
  domain: 'plc' | 'hmi' | 'hmi-plc-cross';
  location: string;
  variable?: string;
  description: string;
  suggestion: string;
  relatedVariables?: string[];
  relatedScreens?: string[];
  reference?: string;
}

// === プログラム解析結果 ===
export interface ProgramSection {
  name: string;
  language: string;
  description: string;
  explanation: string;
  flowchartSteps: FlowchartElement[];
  keyVariables: { name: string; type: string; description: string }[];
  designPatterns: string[];
}

export interface ProgramAnalysisResult {
  overview: string;
  sections: ProgramSection[];
}

// === アップロード ===
export interface UploadedFile {
  id: string;
  name: string;
  type: 'smc2' | 'csv' | 'st' | 'txt' | 'pdf' | 'image' | 'unknown';
  size: number;
  uploadedAt: string;
}

export interface ProjectData {
  projectId: string;
  files: UploadedFile[];
  smc2Project?: Smc2Project;
  analysisResult?: AnalysisResult;
  programAnalysis?: ProgramAnalysisResult;
  screenshotAnalyses?: ScreenshotAnalysis[];
  diagnosisResult?: ComprehensiveDiagnosisResult;
}

export interface ScreenshotAnalysis {
  fileName: string;
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

// === チャット ===
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  images?: string[];
  timestamp: string;
}

// === ラダー図 ===
export interface LadderRung {
  number: number;
  comment: string;
  elements: LadderElement[];
  coil: LadderCoil;
}

export interface LadderElement {
  type: 'NO' | 'NC' | 'TIMER' | 'COUNTER' | 'FB' | 'COMPARE' | 'PARALLEL_START' | 'PARALLEL_END';
  variable: string;
  label?: string;
  value?: string;
}

export interface LadderCoil {
  type: 'OUT' | 'SET' | 'RESET' | 'TIMER' | 'COUNTER' | 'FB_CALL';
  variable: string;
  label?: string;
}

// === プログラム生成 ===
export interface GeneratedProgram {
  code: string;
  language: 'ST' | 'LD';
  explanation: string;
  variables: GeneratedVariable[];
  safetyNotes: string[];
  testProcedures: string[];
  ladderRungs?: LadderRung[];
  flowchart?: string;
  flowchartSteps?: FlowchartElement[];
}

// === フローチャート（構造化データ） ===
export interface FlowchartItem {
  type: 'start' | 'end' | 'process' | 'decision' | 'subprocess';
  label: string;
  description?: string;
  deviceId?: string;
  branchYes?: string;
  branchNo?: string;
}

export interface FlowchartParallel {
  type: 'parallel';
  branches: FlowchartItem[][];
}

export type FlowchartElement = FlowchartItem | FlowchartParallel;

export interface GeneratedVariable {
  name: string;
  type: string;
  description: string;
  initialValue?: string;
}

// === 総合診断 ===
export interface ComprehensiveDiagnosisResult {
  phenomena: DiagnosisPhenomenon[];
  rootCauseAnalysis: RootCauseAnalysis[];
  countermeasures: Countermeasure[];
  summary: string;
}

export interface DiagnosisPhenomenon {
  id: string;
  screenshotIndex: number;
  errorType: string;
  description: string;
  errorCode?: string;
  affectedDevice?: string;
}

export interface RootCauseAnalysis {
  id: string;
  relatedPhenomena: string[];
  location: string;
  description: string;
  probability: 'high' | 'medium' | 'low';
  relatedVariables?: string[];
}

export interface Countermeasure {
  id: string;
  priority: 1 | 2 | 3;
  relatedCauses: string[];
  title: string;
  description: string;
  implementation: string;
  risk: string;
}

// === タブ ===
export type TabId = 'plc' | 'hmi' | 'crossref' | 'transition' | 'screenshot' | 'generate' | 'programAnalysis' | 'diagnosis';
