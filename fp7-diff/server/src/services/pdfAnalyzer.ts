/**
 * PDFのラダー図ページを抽出し、差分があるページのみAI Visionで解析
 * （オプション機能・PDFアップロード時のみ動作）
 *
 * 注: PyMuPDFが必要なため、Pythonサブプロセスで処理する想定。
 *     初版はPDF未アップロード時にスキップする実装に留め、
 *     PDF統合は次フェーズで対応。
 */

export interface PdfAnalysisResult {
  pageCount: number;
  diffPages: number[];
  pageSummaries: { page: number; summary: string }[];
  enabled: boolean;
  message: string;
}

// 初版: PDF解析はプレースホルダ（次フェーズで実装）
export function analyzePdfDiff(_pdfPathA: string | null, _pdfPathB: string | null): PdfAnalysisResult {
  return {
    pageCount: 0,
    diffPages: [],
    pageSummaries: [],
    enabled: false,
    message: 'PDF差分解析は次フェーズで対応予定です。現在は変数・コメント・I/Oの比較のみ対応しています。',
  };
}
