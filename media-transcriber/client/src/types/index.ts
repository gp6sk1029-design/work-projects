// 音声モード
export type AudioMode = 'face_to_face' | 'phone_call' | 'unknown';

// 要約タイプ
export type SummaryType = 'brief' | 'detailed' | 'minutes' | 'action_items';

// メインタブ
export type MainTab = 'transcript' | 'summary' | 'sections' | 'mindmap';

// 処理ステップ
export interface ProcessingStep {
  step: string;
  status: 'waiting' | 'processing' | 'done' | 'error';
  message: string;
  progress?: number;
}

// 録音データ
export interface Recording {
  id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  duration_seconds: number;
  audio_mode: AudioMode;
  audio_analysis: string;
  is_video: boolean;
  created_at: string;
  updated_at: string;
}

// 文字起こしセグメント
export interface TranscriptSegment {
  start: number;
  end: number;
  speaker?: string;
  text: string;
}

// 文字起こし
export interface Transcription {
  id: string;
  recording_id: string;
  full_text: string;
  segments: TranscriptSegment[];
  language: string;
  created_at: string;
}

// 要約
export interface SummaryData {
  id: string;
  recording_id: string;
  summary_type: SummaryType;
  content: string;
  created_at: string;
}

// セクション
export interface Section {
  id: string;
  recording_id: string;
  section_index: number;
  title: string;
  start_time: number;
  end_time: number;
  transcript_text: string;
  summary: string;
  mindmap_mermaid: string;
  user_comment: string;
  created_at: string;
}

// チャットメッセージ
export interface ChatMessage {
  id: string;
  recording_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

// マインドマップ
export interface MindmapData {
  id: string;
  recording_id: string;
  section_id: string | null;
  mermaid_code: string;
  created_at: string;
}

// 履歴アイテム
export interface HistoryItem {
  id: string;
  file_name: string;
  duration_seconds: number;
  audio_mode: AudioMode;
  is_video: boolean;
  created_at: string;
  has_transcription: boolean;
}

// 録音詳細（全関連データ）
export interface RecordingDetail {
  recording: Recording;
  transcription: Transcription | null;
  summaries: SummaryData[];
  sections: Section[];
  chatMessages: ChatMessage[];
  mindmaps: MindmapData[];
}

// アプリ全体の状態
export type AppView = 'upload' | 'processing' | 'result';
