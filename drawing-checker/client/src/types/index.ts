export type Severity = 'error' | 'warning' | 'info';

export interface Finding {
  checker: string;
  rule_id: string;
  severity: Severity;
  message: string;
  page_number: number;
  bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  suggestion?: string;
  jis_reference?: string;
}

export interface CheckResult {
  drawing_path: string;
  drawing_name: string;
  checked_pdf_path: string | null;
  pass: boolean;
  errors_count: number;
  warnings_count: number;
  info_count: number;
  processing_time_sec: number;
  findings: Finding[];
}

export interface CheckResponse {
  ok: boolean;
  resultId: string;
  result: CheckResult;
  pdfUrl: string | null;
  pdfName: string | null;
  originalUrl: string;
  originalName: string;
}

export interface LearnResponse {
  ok: boolean;
  exitCode: number;
  filesLearned: number;
  rulesCount: number;
  stderr?: string;
  learned?: { rules: any[] };
}

export interface SampleItem {
  batchId: string;
  filename: string;
  uploaded_at: string;
  size_bytes: number;
  url: string;
}

export interface SamplesResponse {
  count: number;
  totalBytes: number;
  items: SampleItem[];
}

export interface InfoResponse {
  jisRulesCount: number;
  learnedRulesCount: number;
  hasLearnedRules: boolean;
}
