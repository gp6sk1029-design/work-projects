export type DiffStatus = 'added' | 'removed' | 'changed' | 'same';

export type DeviceCategory =
  | 'X' | 'Y' | 'R' | 'L' | 'T' | 'C'
  | 'DT' | 'LD' | 'SD' | 'SR' | 'FL' | 'P'
  | 'WX' | 'WY' | 'WR' | 'OTHER';

export interface DiffRow {
  address: string;
  category: DeviceCategory;
  status: DiffStatus;
  commentA: string;
  commentB: string;
}

export interface DiffSummary {
  total: number;
  byStatus: Record<DiffStatus, number>;
  byCategory: Record<DeviceCategory, Record<DiffStatus, number>>;
}

export interface DiffResult {
  rows: DiffRow[];
  summary: DiffSummary;
  metadata: {
    projectAName: string;
    projectBName: string;
    countA: number;
    countB: number;
    generatedAt: string;
  };
}

export interface AiSummary {
  overview: string;
  mainChanges: { title: string; description: string; impact: string }[];
  patterns: { name: string; description: string; examples: string[] }[];
  risks: { description: string; severity: 'high' | 'medium' | 'low' }[];
  recommendations: string[];
}

export interface CompareResponse {
  id: string;
  diff: DiffResult;
  aiSummary: AiSummary | null;
}
