/**
 * PDFラダー図 視覚比較ビュー
 *  - 2つのPDFをアップロード
 *  - 各ページをPython側でPNG化＋差分検出（220dpi）
 *  - 左右並列＋差分ページマーク＋ピクセル差分赤枠
 *  - ズーム3段階/全画面/左右スクロール同期で文字潰れなく詳細確認
 */
import { useState, useMemo, useRef, useEffect } from 'react';
import type { PdfDiffResponse, PdfMatch, PdfPageInfo } from '../types/pdfDiff';

const STATUS_LABEL: Record<PdfMatch['status'], { label: string; color: string; emoji: string }> = {
  exact:   { label: '完全一致', color: 'text-gray-500',   emoji: '⚪' },
  similar: { label: '差分あり',  color: 'text-yellow-400', emoji: '🟡' },
  a_only:  { label: 'Aのみ',     color: 'text-red-400',    emoji: '🔴' },
  b_only:  { label: 'Bのみ',     color: 'text-green-400',  emoji: '🟢' },
};

type FilterMode = 'all' | 'diff' | 'similar' | 'only_a' | 'only_b';
type ZoomMode = 'fit' | '100' | '200';

export default function PdfDiffViewer() {
  const [pdfA, setPdfA] = useState<File | null>(null);
  const [pdfB, setPdfB] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PdfDiffResponse | null>(null);
  const [selectedMatchIdx, setSelectedMatchIdx] = useState<number | null>(null);
  const [filter, setFilter] = useState<FilterMode>('diff');
  const [showOverlay, setShowOverlay] = useState(true);
  const [zoom, setZoom] = useState<ZoomMode>('fit');
  const [syncScroll, setSyncScroll] = useState(true);
  const [fullscreenImage, setFullscreenImage] = useState<string | null>(null);

  const handleCompare = async () => {
    if (!pdfA || !pdfB) {
      setError('PDF A と B の両方を指定してください');
      return;
    }
    setError(null);
    setIsLoading(true);
    setResult(null);
    setSelectedMatchIdx(null);
    try {
      const fd = new FormData();
      fd.append('pdfA', pdfA);
      fd.append('pdfB', pdfB);
      const res = await fetch('/api/pdf-diff', { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json();
        setError(err.error || 'PDF差分処理に失敗しました');
        return;
      }
      const data: PdfDiffResponse = await res.json();
      setResult(data);
      const firstDiff = data.matches.findIndex((m) => m.status === 'similar');
      if (firstDiff >= 0) setSelectedMatchIdx(firstDiff);
    } catch (err) {
      setError(`通信エラー: ${String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredMatches = useMemo(() => {
    if (!result) return [];
    return result.matches
      .map((m, idx) => ({ m, idx }))
      .filter(({ m }) => {
        if (filter === 'all') return true;
        if (filter === 'diff') return m.status !== 'exact';
        if (filter === 'similar') return m.status === 'similar';
        if (filter === 'only_a') return m.status === 'a_only';
        if (filter === 'only_b') return m.status === 'b_only';
        return true;
      });
  }, [result, filter]);

  const selected = result && selectedMatchIdx !== null ? result.matches[selectedMatchIdx] : null;

  const imageUrl = (filename: string) =>
    result ? `${result.imageBaseUrl}/${encodeURIComponent(filename)}` : '';

  // キーボード操作（J/K で前後ページ、F でフルスクリーン）
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!result || selectedMatchIdx === null) return;
      if (e.target && (e.target as HTMLElement).tagName === 'INPUT') return;
      const list = filteredMatches.map((x) => x.idx);
      const pos = list.indexOf(selectedMatchIdx);
      if (e.key === 'j' || e.key === 'ArrowDown') {
        if (pos < list.length - 1) setSelectedMatchIdx(list[pos + 1]);
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        if (pos > 0) setSelectedMatchIdx(list[pos - 1]);
      } else if (e.key === '1') setZoom('fit');
      else if (e.key === '2') setZoom('100');
      else if (e.key === '3') setZoom('200');
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [result, selectedMatchIdx, filteredMatches]);

  return (
    <div className="space-y-4">
      {/* アップロード */}
      <div className="p-4 bg-dark-surface rounded border border-dark-border">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          📤 比較する2つのラダー印刷PDFをアップロード
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PdfDropZone label="PDF A（基準）" file={pdfA} onChange={setPdfA} />
          <PdfDropZone label="PDF B（比較対象）" file={pdfB} onChange={setPdfB} />
        </div>
        <div className="mt-3 flex justify-end">
          <button
            onClick={handleCompare}
            disabled={!pdfA || !pdfB || isLoading}
            className="px-6 py-2 bg-accent-600 hover:bg-accent-500 disabled:bg-accent-600/30 disabled:text-gray-500 text-white font-semibold rounded transition"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                解析中...（高解像度220dpi、初回30秒〜数分）
              </span>
            ) : (
              'PDF比較を実行'
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded text-red-300 text-sm">
          ⚠️ {error}
        </div>
      )}

      {result && (
        <>
          {/* サマリ */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatTile label="A総ページ" value={result.summary.pagesA} color="text-gray-300" />
            <StatTile label="B総ページ" value={result.summary.pagesB} color="text-gray-300" />
            <StatTile label="🟡 差分あり" value={result.summary.similarMatches} color="text-yellow-400" />
            <StatTile label="🔴 Aのみ" value={result.summary.onlyInA} color="text-red-400" />
            <StatTile label="🟢 Bのみ" value={result.summary.onlyInB} color="text-green-400" />
          </div>

          {/* メインビュー（横方向もリサイズ可能なフレックスレイアウト） */}
          <div className="flex flex-col lg:flex-row gap-3 items-stretch">
            {/* ページ一覧（左サイドバー、横方向リサイズ可） */}
            <div
              className="bg-dark-surface rounded border border-dark-border p-2 overflow-y-auto flex-shrink-0"
              style={{
                width: '210px',
                resize: 'horizontal',
                maxHeight: '85vh',
                minWidth: '140px',
                maxWidth: '400px',
              }}
              title="右端をドラッグで幅調整">
              <div className="flex flex-wrap gap-1 mb-2 sticky top-0 bg-dark-surface pb-2 z-10">
                {([
                  ['diff', '差分のみ'],
                  ['all', '全件'],
                  ['similar', '🟡'],
                  ['only_a', '🔴'],
                  ['only_b', '🟢'],
                ] as [FilterMode, string][]).map(([k, l]) => (
                  <button
                    key={k}
                    onClick={() => setFilter(k)}
                    className={`px-2 py-1 text-xs rounded transition ${
                      filter === k ? 'bg-accent-600 text-white' : 'bg-dark-bg text-gray-400 hover:text-white'
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mb-2">{filteredMatches.length} 件</p>
              <ul className="space-y-1">
                {filteredMatches.map(({ m, idx }) => {
                  const info = STATUS_LABEL[m.status];
                  const aPage = m.aIndex !== null ? result.pagesA[m.aIndex]?.pageNumber : null;
                  const bPage = m.bIndex !== null ? result.pagesB[m.bIndex]?.pageNumber : null;
                  return (
                    <li key={idx}>
                      <button
                        onClick={() => setSelectedMatchIdx(idx)}
                        className={`w-full text-left p-2 rounded text-xs transition ${
                          selectedMatchIdx === idx
                            ? 'bg-accent-600/40 border border-accent-400'
                            : 'bg-dark-bg hover:bg-dark-hover/40 border border-transparent'
                        }`}
                      >
                        <span className={`font-semibold ${info.color}`}>{info.emoji}</span>
                        <span className="ml-1 text-gray-400">A:{aPage ?? '—'} / B:{bPage ?? '—'}</span>
                        {m.pixelDiff && m.pixelDiff.rects.length > 0 && (
                          <div className="text-yellow-300 mt-0.5">差分{m.pixelDiff.rects.length}箇所</div>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>

            {/* 拡大表示（メイン・残り幅を全部使う） */}
            <div className="flex-1 min-w-0 bg-dark-surface rounded border border-dark-border p-3">
              {/* ツールバー */}
              <div className="flex items-center justify-between flex-wrap gap-2 mb-3 pb-3 border-b border-dark-border">
                {selected && (
                  <div className="text-sm">
                    <span className={`font-semibold ${STATUS_LABEL[selected.status].color}`}>
                      {STATUS_LABEL[selected.status].emoji} {STATUS_LABEL[selected.status].label}
                    </span>
                    {selected.pixelDiff && (
                      <span className="ml-3 text-xs text-gray-400">
                        差分エリア {selected.pixelDiff.rects.length}箇所・変化率 {(selected.pixelDiff.changedRatio * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                )}

                <div className="flex items-center gap-3 text-xs">
                  {/* ズーム切替 */}
                  <div className="flex items-center gap-1 bg-dark-bg rounded p-0.5">
                    {([
                      ['fit', 'フィット'],
                      ['100', '100%'],
                      ['200', '200%'],
                    ] as [ZoomMode, string][]).map(([k, l]) => (
                      <button
                        key={k}
                        onClick={() => setZoom(k)}
                        className={`px-2 py-1 rounded text-xs transition ${
                          zoom === k ? 'bg-accent-600 text-white' : 'text-gray-400 hover:text-white'
                        }`}
                        title={`ショートカット: ${k === 'fit' ? '1' : k === '100' ? '2' : '3'}`}
                      >
                        {l}
                      </button>
                    ))}
                  </div>

                  {/* スクロール同期 */}
                  <label className="flex items-center gap-1.5 text-gray-300 cursor-pointer">
                    <input type="checkbox" checked={syncScroll} onChange={() => setSyncScroll(!syncScroll)} />
                    🔗 同期スクロール
                  </label>

                  {/* 赤枠ON/OFF */}
                  {selected?.pixelDiff && (
                    <label className="flex items-center gap-1.5 text-gray-300 cursor-pointer">
                      <input type="checkbox" checked={showOverlay} onChange={() => setShowOverlay(!showOverlay)} />
                      🟥 赤枠
                    </label>
                  )}
                </div>
              </div>

              {!selected ? (
                <p className="text-center text-gray-500 py-12 text-sm">左の一覧からページを選択してください</p>
              ) : (
                <PageComparisonView
                  match={selected}
                  pagesA={result.pagesA}
                  pagesB={result.pagesB}
                  imageUrl={imageUrl}
                  showOverlay={showOverlay}
                  zoom={zoom}
                  syncScroll={syncScroll}
                  onFullscreen={(url) => setFullscreenImage(url)}
                />
              )}

              <div className="mt-3 pt-3 border-t border-dark-border text-xs text-gray-500">
                💡 ショートカット: <kbd className="px-1.5 py-0.5 bg-dark-bg rounded">J/↓</kbd> 次 /
                <kbd className="ml-1 px-1.5 py-0.5 bg-dark-bg rounded">K/↑</kbd> 前 /
                <kbd className="ml-1 px-1.5 py-0.5 bg-dark-bg rounded">1/2/3</kbd> ズーム /
                画像クリックで全画面
              </div>
            </div>
          </div>
        </>
      )}

      {/* 全画面モーダル */}
      {fullscreenImage && (
        <div
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center p-4 cursor-zoom-out"
          onClick={() => setFullscreenImage(null)}
        >
          <button
            className="absolute top-4 right-4 px-3 py-1.5 bg-dark-surface hover:bg-dark-hover text-white rounded text-sm"
            onClick={() => setFullscreenImage(null)}
          >
            ✕ 閉じる
          </button>
          <div className="max-w-[95vw] max-h-[95vh] overflow-auto">
            <img src={fullscreenImage} alt="拡大" className="max-w-none" />
          </div>
        </div>
      )}
    </div>
  );
}

function PdfDropZone({ label, file, onChange }: { label: string; file: File | null; onChange: (f: File | null) => void; }) {
  const [drag, setDrag] = useState(false);
  return (
    <label
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) onChange(f); }}
      className={`cursor-pointer border-2 border-dashed rounded-lg p-4 transition block ${
        drag ? 'border-accent-400 bg-accent-500/10' : 'border-dark-border bg-dark-bg hover:bg-dark-hover/20'
      }`}
      style={{ borderColor: file ? '#10b981' : undefined }}
    >
      <input type="file" accept=".pdf" className="hidden" onChange={(e) => onChange(e.target.files?.[0] || null)} />
      <div className="text-center">
        <div className="text-2xl mb-1">{file ? '✅' : '📄'}</div>
        <p className="text-xs text-gray-300 font-semibold mb-1">{label}</p>
        {file ? (
          <>
            <p className="text-xs text-green-400 break-all">{file.name}</p>
            <p className="text-xs text-gray-500 mt-1">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
          </>
        ) : (
          <p className="text-xs text-gray-500">PDFをドロップ or クリック</p>
        )}
      </div>
    </label>
  );
}

function StatTile({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="p-3 bg-dark-surface rounded border border-dark-border">
      <div className="text-xs text-gray-400">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  );
}

function PageComparisonView({
  match, pagesA, pagesB, imageUrl, showOverlay, zoom, syncScroll, onFullscreen,
}: {
  match: PdfMatch;
  pagesA: PdfPageInfo[];
  pagesB: PdfPageInfo[];
  imageUrl: (f: string) => string;
  showOverlay: boolean;
  zoom: ZoomMode;
  syncScroll: boolean;
  onFullscreen: (url: string) => void;
}) {
  const pageA = match.aIndex !== null ? pagesA[match.aIndex] : null;
  const pageB = match.bIndex !== null ? pagesB[match.bIndex] : null;

  const imgAFile = match.pixelDiff && showOverlay ? match.pixelDiff.diffImageA : pageA?.filename;
  const imgBFile = match.pixelDiff && showOverlay ? match.pixelDiff.diffImageB : pageB?.filename;

  const scrollARef = useRef<HTMLDivElement>(null);
  const scrollBRef = useRef<HTMLDivElement>(null);

  // 左右スクロール同期
  useEffect(() => {
    if (!syncScroll) return;
    const a = scrollARef.current;
    const b = scrollBRef.current;
    if (!a || !b) return;
    let lock = false;
    const onA = () => {
      if (lock) return;
      lock = true;
      b.scrollTop = a.scrollTop;
      b.scrollLeft = a.scrollLeft;
      requestAnimationFrame(() => { lock = false; });
    };
    const onB = () => {
      if (lock) return;
      lock = true;
      a.scrollTop = b.scrollTop;
      a.scrollLeft = b.scrollLeft;
      requestAnimationFrame(() => { lock = false; });
    };
    a.addEventListener('scroll', onA);
    b.addEventListener('scroll', onB);
    return () => {
      a.removeEventListener('scroll', onA);
      b.removeEventListener('scroll', onB);
    };
  }, [syncScroll]);

  // ズームに応じた画像のスタイル
  const imgStyle: React.CSSProperties = zoom === 'fit'
    ? { width: '100%', height: 'auto', display: 'block' }
    : zoom === '100'
      ? { width: 'auto', height: 'auto', maxWidth: 'none', display: 'block' }
      : { width: '200%', height: 'auto', maxWidth: 'none', display: 'block' };

  return (
    // 外側のwrapperを「縦に」リサイズ可能に（高さをマウスで調整）
    <div
      style={{
        resize: 'vertical',
        overflow: 'hidden',
        height: '78vh',
        minHeight: '300px',
        maxHeight: '95vh',
      }}
      className="border border-dark-border/50 rounded relative"
      title="右下隅をドラッグで高さ調整"
    >
      {/*
        flexbox にして、各コラムが個別にリサイズできるようにする
        （grid-cols-2 だと幅が1frに固縛され、子のresizeが効かない）
      */}
      <div style={{ display: 'flex', gap: '12px', height: '100%', padding: '4px', overflow: 'hidden' }}>
        <PageColumn
          title={`A: p${pageA?.pageNumber ?? '—'}`}
          src={imgAFile ? imageUrl(imgAFile) : null}
          headerText={pageA?.headerText || ''}
          scrollRef={scrollARef}
          imgStyle={imgStyle}
          onFullscreen={onFullscreen}
        />
        <PageColumn
          title={`B: p${pageB?.pageNumber ?? '—'}`}
          src={imgBFile ? imageUrl(imgBFile) : null}
          headerText={pageB?.headerText || ''}
          scrollRef={scrollBRef}
          imgStyle={imgStyle}
          onFullscreen={onFullscreen}
        />
      </div>
      {/* リサイズハンドルの目印 */}
      <div className="absolute bottom-0 right-0 w-4 h-4 pointer-events-none flex items-end justify-end pr-0.5 pb-0.5">
        <svg width="10" height="10" viewBox="0 0 10 10" className="text-accent-400">
          <path d="M0 10 L10 0 M3 10 L10 3 M6 10 L10 6" stroke="currentColor" strokeWidth="1" fill="none" />
        </svg>
      </div>
    </div>
  );
}

function PageColumn({
  title, src, headerText, scrollRef, imgStyle, onFullscreen,
}: {
  title: string;
  src: string | null;
  headerText: string;
  scrollRef: React.RefObject<HTMLDivElement>;
  imgStyle: React.CSSProperties;
  onFullscreen: (url: string) => void;
}) {
  // JS手動リサイズ（CSS resize は flex item で動かないため）
  // null = 初期値（flex: 1 で50/50均等）、数値が入ったら明示サイズ
  const [width, setWidth] = useState<number | null>(null);
  const [height, setHeight] = useState<number | null>(null);
  const colRef = useRef<HTMLDivElement>(null);

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!colRef.current) return;
    const rect = colRef.current.getBoundingClientRect();
    const startX = e.clientX;
    const startY = e.clientY;
    const startW = rect.width;
    const startH = rect.height;

    const onMove = (ev: MouseEvent) => {
      const newW = Math.max(200, startW + (ev.clientX - startX));
      const newH = Math.max(200, startH + (ev.clientY - startY));
      setWidth(newW);
      setHeight(newH);
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'nwse-resize';
  };

  const resetSize = () => { setWidth(null); setHeight(null); };

  // サイズ未指定なら flex: 1 で均等、指定後は固定px
  const wrapperStyle: React.CSSProperties = {
    flex: width !== null ? `0 0 ${width}px` : '1 1 0',
    width: width !== null ? `${width}px` : undefined,
    height: height !== null ? `${height}px` : '100%',
    minWidth: '200px',
    minHeight: '200px',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    overflow: 'hidden',
  };

  return (
    <div
      ref={colRef}
      style={wrapperStyle}
      className="bg-dark-bg/30 rounded border border-dark-border/40"
    >
      <div className="text-xs text-gray-400 px-2 pt-1.5 pb-1 flex items-center justify-between flex-shrink-0">
        <span className="font-semibold text-white">{title}</span>
        {headerText && (
          <span className="text-[10px] text-gray-500 truncate ml-2 max-w-[60%]" title={headerText}>
            {headerText.substring(0, 80)}
          </span>
        )}
      </div>
      {/* 内側 = スクロール専用 */}
      <div
        ref={scrollRef}
        className="bg-white rounded-b overflow-auto"
        style={{ flex: 1, minHeight: 0 }}
      >
        {src ? (
          <img
            src={src}
            alt={title}
            style={imgStyle}
            className="cursor-zoom-in"
            onClick={() => onFullscreen(src)}
          />
        ) : (
          <div className="p-12 text-center text-gray-500 bg-dark-bg">
            （該当ページなし）
          </div>
        )}
      </div>

      {/* 右下隅リサイズハンドル（手動JS実装・確実動作） */}
      <div
        onMouseDown={startResize}
        onDoubleClick={resetSize}
        title="ドラッグでサイズ変更 / ダブルクリックでリセット"
        style={{
          position: 'absolute',
          right: 0,
          bottom: 0,
          width: '20px',
          height: '20px',
          cursor: 'nwse-resize',
          background: 'linear-gradient(135deg, transparent 50%, #60a5fa 50%, #60a5fa 60%, transparent 60%, transparent 70%, #60a5fa 70%, #60a5fa 80%, transparent 80%)',
          zIndex: 10,
        }}
      />
      {/* 右辺リサイズハンドル（横方向のみ） */}
      <div
        onMouseDown={startResize}
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          bottom: '20px',
          width: '4px',
          cursor: 'ew-resize',
          background: 'transparent',
          zIndex: 9,
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(96,165,250,0.4)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      />
      {/* 下辺リサイズハンドル（縦方向のみ） */}
      <div
        onMouseDown={startResize}
        style={{
          position: 'absolute',
          left: 0,
          right: '20px',
          bottom: 0,
          height: '4px',
          cursor: 'ns-resize',
          background: 'transparent',
          zIndex: 9,
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(96,165,250,0.4)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      />
    </div>
  );
}
