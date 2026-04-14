// 音声モード
export type AudioMode = 'face_to_face' | 'phone_call' | 'unknown';

// 要約タイプ
export type SummaryType = 'brief' | 'detailed' | 'minutes' | 'action_items';

// 音声分析結果
export interface AudioAnalysis {
  sampleRate: number;
  channels: number;
  bitrate: number;
  codec: string;
  duration: number;
  format: string;
}

// 録音レコード
export interface Recording {
  id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  duration_seconds: number;
  audio_mode: AudioMode;
  audio_analysis: string; // JSON
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

// 文字起こしレコード
export interface Transcription {
  id: string;
  recording_id: string;
  full_text: string;
  segments: string; // JSON: TranscriptSegment[]
  language: string;
  created_at: string;
}

// 要約レコード
export interface Summary {
  id: string;
  recording_id: string;
  summary_type: SummaryType;
  content: string;
  created_at: string;
}

// セクションレコード
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
export interface Mindmap {
  id: string;
  recording_id: string;
  section_id: string | null;
  mermaid_code: string;
  created_at: string;
}

// SSE進捗イベント
export interface ProgressEvent {
  step: string;
  status: 'waiting' | 'processing' | 'done' | 'error';
  message: string;
  progress?: number; // 0-100
}
