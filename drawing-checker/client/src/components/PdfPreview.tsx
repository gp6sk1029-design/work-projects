import { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import type { Finding } from '../types';

// PDF.js worker の設定：CDN経由の方が確実（Viteの静的解析を経由しない）
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface Props {
  pdfUrl: string | null;
  originalUrl: string;
  originalName: string;
  findings: Finding[];
  selectedIndex: number | null;
}

export default function PdfPreview({ pdfUrl, originalUrl, originalName, findings, selectedIndex }: Props) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<{ w: number; h: number } | null>(null);
  const [mode, setMode] = useState<'checked' | 'original'>('checked');
  const [scale, setScale] = useState(1.2);
  const containerRef = useRef<HTMLDivElement>(null);

  // 使用するURL（注釈PDFがあればそれ、なければ元ファイル）
  const url = mode === 'checked' && pdfUrl ? pdfUrl : originalUrl;
  // 元ファイルがPDF以外（画像/DXF/DWG/SLDDRW）の場合、checkedのみが閲覧可能
  const isOriginalPdf = /\.pdf$/i.test(originalName);

  useEffect(() => {
    if (!isOriginalPdf) setMode('checked');
  }, [originalName, isOriginalPdf]);

  // 選択中のfindingのページへジャンプ
  useEffect(() => {
    if (selectedIndex != null) {
      const f = findings[selectedIndex];
      if (f && f.page_number > 0 && f.page_number <= numPages) {
        setCurrentPage(f.page_number);
      }
    }
  }, [selectedIndex, findings, numPages]);

  // 注釈PDFは1ページ目がサマリなので、findingsは page+1 にマッピングされている可能性あり
  // 指摘の多くは page 2以降に表示される
  const overlayFindings = findings.filter(f => {
    // サマリーページオフセット：checkedモードの場合 findings.page_number+1 が実ページ
    const targetPage = mode === 'checked' && pdfUrl ? (f.page_number + 1) : f.page_number;
    return targetPage === currentPage;
  });

  return (
    <div className="rounded-xl bg-dark-surface border border-dark-border overflow-hidden flex flex-col h-[calc(100vh-8rem)]">
      {/* ツールバー */}
      <div className="px-4 py-2 border-b border-dark-border flex items-center gap-2 text-sm">
        <div className="flex bg-dark-bg rounded-md overflow-hidden border border-dark-border">
          <button
            onClick={() => setMode('checked')}
            disabled={!pdfUrl}
            className={`px-3 py-1 ${mode === 'checked' ? 'bg-accent text-slate-900 font-medium' : 'text-slate-300'} disabled:opacity-40`}
          >
            赤ペン注釈
          </button>
          <button
            onClick={() => setMode('original')}
            disabled={!isOriginalPdf}
            className={`px-3 py-1 ${mode === 'original' ? 'bg-accent text-slate-900 font-medium' : 'text-slate-300'} disabled:opacity-40`}
          >
            元図面
          </button>
        </div>

        {numPages > 1 && (
          <div className="flex items-center gap-2 ml-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              className="px-2 py-1 rounded bg-dark-bg hover:bg-dark-hover"
            >
              ◀
            </button>
            <span className="text-xs text-slate-400">
              {currentPage} / {numPages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))}
              className="px-2 py-1 rounded bg-dark-bg hover:bg-dark-hover"
            >
              ▶
            </button>
          </div>
        )}

        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => setScale(s => Math.max(0.4, s - 0.2))}
            className="px-2 py-1 rounded bg-dark-bg hover:bg-dark-hover"
          >
            −
          </button>
          <span className="text-xs text-slate-400 w-12 text-center">{(scale * 100).toFixed(0)}%</span>
          <button
            onClick={() => setScale(s => Math.min(3, s + 0.2))}
            className="px-2 py-1 rounded bg-dark-bg hover:bg-dark-hover"
          >
            ＋
          </button>
        </div>
      </div>

      {/* プレビュー */}
      <div className="flex-1 overflow-auto bg-slate-950/50 flex items-start justify-center p-4" ref={containerRef}>
        <div className="relative inline-block">
          <Document
            file={url}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
            onLoadError={(err) => console.error('PDF load error:', err)}
            loading={<div className="p-12 text-slate-400">読み込み中...</div>}
            error={
              <div className="p-12 text-slate-400 text-center max-w-md">
                <div className="text-4xl mb-2">📄</div>
                <div className="text-sm mb-2">PDFの表示に失敗しました</div>
                <div className="text-xs text-slate-500 mb-3">
                  ブラウザのキャッシュをクリアしてリロード（Ctrl+F5）してみてください。
                  それでも表示されない場合は下のボタンからダウンロードして直接開いてください。
                </div>
                <a
                  href={url}
                  download
                  className="inline-block px-3 py-1.5 rounded bg-accent text-slate-900 text-xs font-medium"
                >
                  📥 PDFをダウンロード
                </a>
              </div>
            }
          >
            <Page
              pageNumber={currentPage}
              scale={scale}
              renderTextLayer={false}
              renderAnnotationLayer={false}
              onLoadSuccess={(pg) => setPageSize({ w: pg.width, h: pg.height })}
            />
          </Document>

          {/* Canvasの上に赤丸オーバーレイ */}
          {pageSize && overlayFindings.length > 0 && (
            <svg
              className="absolute inset-0 pointer-events-none"
              width={pageSize.w * scale}
              height={pageSize.h * scale}
              viewBox={`0 0 ${pageSize.w * scale} ${pageSize.h * scale}`}
            >
              {overlayFindings.map((f, i) => {
                if (!f.bbox) return null;
                // PDF座標系（左下原点）→ CSS座標（左上原点）に変換
                const x = f.bbox.x0 * scale;
                const y = (pageSize.h - f.bbox.y1) * scale;
                const w = (f.bbox.x1 - f.bbox.x0) * scale;
                const h = (f.bbox.y1 - f.bbox.y0) * scale;
                const color =
                  f.severity === 'error' ? '#ef4444'
                  : f.severity === 'warning' ? '#f59e0b'
                  : '#3b82f6';
                const isSelected = findings[selectedIndex ?? -1] === f;
                return (
                  <g key={i}>
                    <rect
                      x={x - 4}
                      y={y - 4}
                      width={w + 8}
                      height={h + 8}
                      fill="none"
                      stroke={color}
                      strokeWidth={isSelected ? 3 : 2}
                      strokeDasharray={isSelected ? '' : '4 2'}
                      rx={4}
                    />
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}
