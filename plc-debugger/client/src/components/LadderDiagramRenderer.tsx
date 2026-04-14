import { useMemo } from 'react';
import type { LadderRung, LadderElement, LadderCoil } from '../types';

interface Props {
  rungs: LadderRung[];
}

// === 描画定数 ===
const C = {
  // レイアウト
  MARGIN_LEFT: 60,       // ラング番号用の左マージン
  RAIL_X: 60,            // 左パワーレール X座標
  ELEMENT_W: 120,        // 接点1個の幅
  TIMER_W: 180,          // タイマー/カウンタブロック幅
  TIMER_H: 70,           // タイマー/カウンタブロック高さ
  COIL_W: 80,            // コイル領域幅
  RUNG_H: 80,            // 通常ラングの高さ
  RUNG_H_TIMER: 110,     // タイマー含むラングの高さ
  COMMENT_H: 24,         // コメント行の高さ
  WIRE_Y: 40,            // ラング内のワイヤーY位置（上端からの距離）
  RAIL_W: 3,             // パワーレールの太さ

  // 接点記号
  CONTACT_GAP: 14,       // 接点の縦線の間隔
  CONTACT_H: 22,         // 接点の縦線の高さ

  // カラー（Sysmac Studio風・白背景）
  BG: '#ffffff',
  WIRE: '#0066cc',
  RAIL: '#003399',
  TEXT_VAR: '#0000cc',    // 変数名（青）
  TEXT_COMMENT: '#008800', // コメント（緑）
  TEXT_RUNG: '#666666',   // ラング番号
  CONTACT_LINE: '#333333',
  COIL_LINE: '#333333',
  TIMER_BORDER: '#666666',
  TIMER_BG: '#f8f8f8',
  TIMER_LABEL: '#cc6600',
  NC_SLASH: '#cc0000',
  SET_TEXT: '#cc6600',
  RUNG_SEPARATOR: '#cccccc',
  COMMENT_BG: '#fffff0',
  COMMENT_BORDER: '#ddddaa',
} as const;

// === ラングの高さを計算 ===
function getRungHeight(rung: LadderRung): number {
  const hasTimer = rung.elements.some(e => e.type === 'TIMER' || e.type === 'COUNTER' || e.type === 'FB');
  const hasTimerCoil = rung.coil.type === 'TIMER' || rung.coil.type === 'COUNTER' || rung.coil.type === 'FB_CALL';
  const commentH = rung.comment ? C.COMMENT_H : 0;
  const bodyH = (hasTimer || hasTimerCoil) ? C.RUNG_H_TIMER : C.RUNG_H;
  return commentH + bodyH;
}

// === 接点の描画 ===
function ContactSVG({ element, x, wireY }: { element: LadderElement; x: number; wireY: number }) {
  const cx = x + C.ELEMENT_W / 2;
  const isNC = element.type === 'NC';
  const isTimer = element.type === 'TIMER' || element.type === 'COUNTER' || element.type === 'FB';

  if (isTimer) {
    // タイマー/カウンタ/FBブロック
    const bx = x + (C.ELEMENT_W - C.TIMER_W) / 2 + 10;
    const by = wireY - 15;
    const bw = C.TIMER_W - 20;
    const bh = C.TIMER_H;
    const label = element.type === 'TIMER' ? 'TON' : element.type === 'COUNTER' ? 'CTU' : 'FB';

    return (
      <g>
        {/* 左ワイヤー → ブロック */}
        <line x1={x} y1={wireY} x2={bx} y2={wireY} stroke={C.WIRE} strokeWidth={1.5} />
        {/* ブロック本体 */}
        <rect x={bx} y={by} width={bw} height={bh} fill={C.TIMER_BG} stroke={C.TIMER_BORDER} strokeWidth={1.5} />
        {/* ブロック名 */}
        <text x={bx + bw / 2} y={by - 4} textAnchor="middle" fill={C.TEXT_VAR} fontSize={11} fontFamily="monospace" fontWeight="bold">
          {element.variable}
        </text>
        <text x={bx + bw / 2} y={by + 16} textAnchor="middle" fill={C.TIMER_LABEL} fontSize={12} fontFamily="monospace" fontWeight="bold">
          {label}
        </text>
        {/* ピン: In */}
        <text x={bx + 4} y={wireY + 4} fill="#333" fontSize={10} fontFamily="monospace">In</text>
        {/* ピン: Q */}
        <text x={bx + bw - 16} y={wireY + 4} fill="#333" fontSize={10} fontFamily="monospace">Q</text>
        {/* ピン: PT */}
        <text x={bx + 4} y={wireY + 22} fill="#333" fontSize={10} fontFamily="monospace">PT</text>
        {element.value && (
          <text x={bx + 28} y={wireY + 22} fill={C.TIMER_LABEL} fontSize={10} fontFamily="monospace">{element.value}</text>
        )}
        {/* ピン: ET */}
        <text x={bx + bw - 16} y={wireY + 22} fill="#333" fontSize={10} fontFamily="monospace">ET</text>
        <text x={bx + bw + 2} y={wireY + 22} fill="#999" fontSize={9} fontFamily="monospace">→ 変数を入力</text>
        {/* 右ワイヤー ← ブロック */}
        <line x1={bx + bw} y1={wireY} x2={x + C.ELEMENT_W} y2={wireY} stroke={C.WIRE} strokeWidth={1.5} />
        {/* ラベル */}
        {element.label && (
          <text x={cx} y={by + bh + 14} textAnchor="middle" fill={C.TEXT_COMMENT} fontSize={10} fontFamily="sans-serif">
            {element.label}
          </text>
        )}
      </g>
    );
  }

  // NO / NC 接点
  const halfGap = C.CONTACT_GAP / 2;
  const halfH = C.CONTACT_H / 2;

  return (
    <g>
      {/* 左ワイヤー */}
      <line x1={x} y1={wireY} x2={cx - halfGap} y2={wireY} stroke={C.WIRE} strokeWidth={1.5} />
      {/* 左縦線 */}
      <line x1={cx - halfGap} y1={wireY - halfH} x2={cx - halfGap} y2={wireY + halfH} stroke={C.CONTACT_LINE} strokeWidth={2} />
      {/* 右縦線 */}
      <line x1={cx + halfGap} y1={wireY - halfH} x2={cx + halfGap} y2={wireY + halfH} stroke={C.CONTACT_LINE} strokeWidth={2} />
      {/* NC の場合: 斜線 */}
      {isNC && (
        <line x1={cx - halfGap} y1={wireY + halfH} x2={cx + halfGap} y2={wireY - halfH} stroke={C.NC_SLASH} strokeWidth={1.5} />
      )}
      {/* 右ワイヤー */}
      <line x1={cx + halfGap} y1={wireY} x2={x + C.ELEMENT_W} y2={wireY} stroke={C.WIRE} strokeWidth={1.5} />
      {/* 変数名（上） */}
      <text x={cx} y={wireY - halfH - 6} textAnchor="middle" fill={C.TEXT_VAR} fontSize={11} fontFamily="monospace" fontWeight="bold">
        {element.variable}
      </text>
      {/* ラベル/コメント（下） */}
      {element.label && (
        <text x={cx} y={wireY + halfH + 14} textAnchor="middle" fill={C.TEXT_COMMENT} fontSize={10} fontFamily="sans-serif">
          {element.label}
        </text>
      )}
    </g>
  );
}

// === コイルの描画 ===
function CoilSVG({ coil, x, wireY }: { coil: LadderCoil; x: number; wireY: number }) {
  const cx = x + C.COIL_W / 2;
  const r = 12;
  const isSet = coil.type === 'SET';
  const isReset = coil.type === 'RESET';
  const isBlock = coil.type === 'TIMER' || coil.type === 'COUNTER' || coil.type === 'FB_CALL';

  if (isBlock) {
    const bx = x + 5;
    const by = wireY - 15;
    const bw = C.COIL_W - 10;
    const bh = 50;
    const label = coil.type === 'TIMER' ? 'TON' : coil.type === 'COUNTER' ? 'CTU' : 'FB';

    return (
      <g>
        <line x1={x} y1={wireY} x2={bx} y2={wireY} stroke={C.WIRE} strokeWidth={1.5} />
        <rect x={bx} y={by} width={bw} height={bh} fill={C.TIMER_BG} stroke={C.TIMER_BORDER} strokeWidth={1.5} />
        <text x={bx + bw / 2} y={by - 4} textAnchor="middle" fill={C.TEXT_VAR} fontSize={10} fontFamily="monospace" fontWeight="bold">
          {coil.variable}
        </text>
        <text x={bx + bw / 2} y={wireY + 4} textAnchor="middle" fill={C.TIMER_LABEL} fontSize={11} fontFamily="monospace" fontWeight="bold">
          {label}
        </text>
        {coil.label && (
          <text x={bx + bw / 2} y={by + bh + 14} textAnchor="middle" fill={C.TEXT_COMMENT} fontSize={10} fontFamily="sans-serif">
            {coil.label}
          </text>
        )}
      </g>
    );
  }

  return (
    <g>
      {/* ワイヤー → コイル */}
      <line x1={x} y1={wireY} x2={cx - r} y2={wireY} stroke={C.WIRE} strokeWidth={1.5} />
      {/* コイル丸括弧 */}
      <circle cx={cx} cy={wireY} r={r} fill="none" stroke={C.COIL_LINE} strokeWidth={2} />
      {/* SET / RESET テキスト */}
      {(isSet || isReset) && (
        <text x={cx} y={wireY + 5} textAnchor="middle" fill={C.SET_TEXT} fontSize={12} fontFamily="monospace" fontWeight="bold">
          {isSet ? 'S' : 'R'}
        </text>
      )}
      {/* コイル → 右レール */}
      <line x1={cx + r} y1={wireY} x2={x + C.COIL_W} y2={wireY} stroke={C.WIRE} strokeWidth={1.5} />
      {/* 変数名（上） */}
      <text x={cx} y={wireY - r - 6} textAnchor="middle" fill={C.TEXT_VAR} fontSize={11} fontFamily="monospace" fontWeight="bold">
        {coil.variable}
      </text>
      {/* ラベル（下） */}
      {coil.label && (
        <text x={cx} y={wireY + r + 14} textAnchor="middle" fill={C.TEXT_COMMENT} fontSize={10} fontFamily="sans-serif">
          {coil.label}
        </text>
      )}
    </g>
  );
}

// === メインコンポーネント ===
export default function LadderDiagramRenderer({ rungs }: Props) {
  // 全体のサイズとレイアウトを計算
  const layout = useMemo(() => {
    if (!rungs || rungs.length === 0) return null;

    // 各ラングの実際の幅を計算してSVG幅を決定
    let maxRungWidth = 0;
    for (const rung of rungs) {
      let w = 0;
      for (const el of rung.elements) {
        const isBlock = el.type === 'TIMER' || el.type === 'COUNTER' || el.type === 'FB';
        w += isBlock ? C.TIMER_W : C.ELEMENT_W;
      }
      maxRungWidth = Math.max(maxRungWidth, w);
    }
    // 左レール + 要素幅 + ワイヤー余白 + コイル + 右余白
    const contentWidth = C.RAIL_X + maxRungWidth + 60 + C.COIL_W + 40;
    const totalWidth = Math.max(contentWidth, 600);
    const rightRailX = totalWidth - 20;

    // 各ラングのY位置を計算
    const rungPositions: { y: number; height: number; wireY: number }[] = [];
    let currentY = 10;

    for (const rung of rungs) {
      const h = getRungHeight(rung);
      const commentOffset = rung.comment ? C.COMMENT_H : 0;
      rungPositions.push({
        y: currentY,
        height: h,
        wireY: currentY + commentOffset + C.WIRE_Y,
      });
      currentY += h;
    }

    const totalHeight = currentY + 10;

    return { totalWidth, totalHeight, rightRailX, rungPositions };
  }, [rungs]);

  if (!rungs || rungs.length === 0 || !layout) {
    return (
      <div className="text-center text-gray-500 py-8">
        <p className="text-sm">ラダー図データがありません</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-dark-border overflow-hidden">
      {/* タイトルバー */}
      <div className="flex items-center gap-2 px-4 py-2 bg-dark-hover border-b border-dark-border">
        <div className="w-3 h-3 rounded-full bg-blue-500" />
        <span className="text-sm text-gray-300 font-bold">ラダーダイアグラム</span>
        <span className="text-xs text-gray-500">（{rungs.length} ラング）</span>
      </div>

      {/* SVGラダー図（白背景） */}
      <div className="overflow-auto" style={{ maxHeight: '700px' }}>
        <svg
          width={layout.totalWidth}
          height={layout.totalHeight}
          viewBox={`0 0 ${layout.totalWidth} ${layout.totalHeight}`}
          style={{ background: C.BG, display: 'block', minWidth: '100%' }}
        >
          {/* 左パワーレール */}
          <line
            x1={C.RAIL_X}
            y1={0}
            x2={C.RAIL_X}
            y2={layout.totalHeight}
            stroke={C.RAIL}
            strokeWidth={C.RAIL_W}
          />
          {/* 右パワーレール */}
          <line
            x1={layout.rightRailX}
            y1={0}
            x2={layout.rightRailX}
            y2={layout.totalHeight}
            stroke={C.RAIL}
            strokeWidth={C.RAIL_W}
          />

          {/* 各ラング */}
          {rungs.map((rung, ri) => {
            const pos = layout.rungPositions[ri];
            const wireY = pos.wireY;
            const commentOffset = rung.comment ? C.COMMENT_H : 0;

            // 要素のx座標計算
            let elemX = C.RAIL_X;
            const elementPositions: number[] = [];
            for (let i = 0; i < rung.elements.length; i++) {
              elementPositions.push(elemX);
              const el = rung.elements[i];
              const isBlock = el.type === 'TIMER' || el.type === 'COUNTER' || el.type === 'FB';
              elemX += isBlock ? C.TIMER_W : C.ELEMENT_W;
            }
            // コイルは右パワーレールの手前に配置
            const coilX = layout.rightRailX - C.COIL_W;

            return (
              <g key={ri}>
                {/* ラング区切り線 */}
                {ri > 0 && (
                  <line
                    x1={0}
                    y1={pos.y}
                    x2={layout.totalWidth}
                    y2={pos.y}
                    stroke={C.RUNG_SEPARATOR}
                    strokeWidth={1}
                    strokeDasharray="4,4"
                  />
                )}

                {/* コメント行 */}
                {rung.comment && (
                  <g>
                    <rect
                      x={C.RAIL_X + 5}
                      y={pos.y + 2}
                      width={layout.rightRailX - C.RAIL_X - 10}
                      height={C.COMMENT_H - 4}
                      fill={C.COMMENT_BG}
                      stroke={C.COMMENT_BORDER}
                      strokeWidth={0.5}
                      rx={2}
                    />
                    <text
                      x={C.RAIL_X + 12}
                      y={pos.y + C.COMMENT_H - 8}
                      fill={C.TEXT_COMMENT}
                      fontSize={11}
                      fontFamily="sans-serif"
                    >
                      {rung.comment}
                    </text>
                  </g>
                )}

                {/* ラング番号 */}
                <text
                  x={C.RAIL_X - 8}
                  y={wireY + 4}
                  textAnchor="end"
                  fill={C.TEXT_RUNG}
                  fontSize={11}
                  fontFamily="monospace"
                >
                  {String(rung.number).padStart(3, '0')}
                </text>

                {/* 左レールからの接続ワイヤー */}
                <line
                  x1={C.RAIL_X}
                  y1={wireY}
                  x2={C.RAIL_X + (rung.elements.length > 0 ? 0 : C.ELEMENT_W)}
                  y2={wireY}
                  stroke={C.WIRE}
                  strokeWidth={1.5}
                />

                {/* 各要素 */}
                {rung.elements.map((el, ei) => (
                  <ContactSVG
                    key={ei}
                    element={el}
                    x={elementPositions[ei]}
                    wireY={wireY}
                  />
                ))}

                {/* 要素 → コイル間のワイヤー */}
                <line
                  x1={elemX}
                  y1={wireY}
                  x2={coilX}
                  y2={wireY}
                  stroke={C.WIRE}
                  strokeWidth={1.5}
                />

                {/* コイル */}
                <CoilSVG coil={rung.coil} x={coilX} wireY={wireY} />

                {/* コイル → 右レールのワイヤー */}
                <line
                  x1={coilX + C.COIL_W}
                  y1={wireY}
                  x2={layout.rightRailX}
                  y2={wireY}
                  stroke={C.WIRE}
                  strokeWidth={1.5}
                />
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
