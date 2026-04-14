import { useMemo } from 'react';
import type { FlowchartElement, FlowchartItem, FlowchartParallel } from '../types';

interface Props {
  steps: FlowchartElement[];
  title?: string;
}

// === 描画定数 ===
const C = {
  NODE_W: 200,          // ノード幅
  START_H: 40,          // 開始/終了ノード高さ
  PROCESS_H: 50,        // 処理ノード高さ
  DECISION_H: 60,       // 分岐ノード高さ（菱形の高さ）
  SUBPROCESS_H: 50,     // サブプロセスノード高さ
  GAP_Y: 50,            // ノード間の縦間隔
  PARALLEL_GAP_X: 200,  // 並列列間の間隔
  MARGIN_TOP: 20,       // 上部マージン
  MARGIN_BOTTOM: 20,    // 下部マージン
  MARGIN_X: 40,         // 左右マージン
  FONT_SIZE: 12,        // フォントサイズ
  LINE_CHARS: 14,       // 1行の最大文字数
  LINE_HEIGHT: 16,      // テキスト行間
  ARROW_SIZE: 6,        // 矢頭サイズ
  PARALLEL_BAR_H: 4,    // 並列処理の太い横線の高さ
  LOOP_OFFSET_X: 40,    // ループバック矢印の右オフセット
  BRANCH_LABEL_SIZE: 10,// 分岐ラベルのフォントサイズ
  STROKE: '#000000',
  FILL_BG: '#ffffff',
  FILL_START: '#f0f0f0',
  FILL_SUBPROCESS: '#f0e6ff',
  FILL_DECISION: '#ffffff',
} as const;

// === テキスト分割（日本語対応） ===
function splitText(text: string, maxChars: number): string[] {
  const lines: string[] = [];
  let remaining = text;
  while (remaining.length > maxChars) {
    lines.push(remaining.slice(0, maxChars));
    remaining = remaining.slice(maxChars);
  }
  if (remaining.length > 0) lines.push(remaining);
  return lines;
}

// === ノード高さ取得 ===
function getNodeHeight(item: FlowchartItem): number {
  switch (item.type) {
    case 'start':
    case 'end':
      return C.START_H;
    case 'decision':
      return C.DECISION_H;
    case 'subprocess':
      return C.SUBPROCESS_H;
    case 'process':
    default:
      return C.PROCESS_H;
  }
}

// === レイアウト計算用の型 ===
interface LayoutNode {
  kind: 'item';
  item: FlowchartItem;
  x: number;
  y: number;
  w: number;
  h: number;
}

interface LayoutParallel {
  kind: 'parallel';
  parallel: FlowchartParallel;
  x: number;
  y: number;
  w: number;
  h: number;
  branches: LayoutNode[][];
  barTopY: number;
  barBottomY: number;
}

type LayoutElement = LayoutNode | LayoutParallel;

// === レイアウト計算 ===
function computeLayout(steps: FlowchartElement[], centerX: number): { elements: LayoutElement[]; totalWidth: number; totalHeight: number } {
  const elements: LayoutElement[] = [];
  let curY = C.MARGIN_TOP;
  let maxWidth = C.NODE_W + C.MARGIN_X * 2;

  for (const step of steps) {
    if (step.type === 'parallel') {
      // 並列処理
      const par = step as FlowchartParallel;
      const branchCount = par.branches.length;
      const totalBranchWidth = branchCount * C.NODE_W + (branchCount - 1) * C.PARALLEL_GAP_X;
      const startX = centerX - totalBranchWidth / 2;

      // 上部バー
      const barTopY = curY;
      curY += C.PARALLEL_BAR_H + C.GAP_Y / 2;

      // 各ブランチのノードを配置
      const layoutBranches: LayoutNode[][] = [];
      let maxBranchHeight = 0;

      for (let bi = 0; bi < branchCount; bi++) {
        const branchX = startX + bi * (C.NODE_W + C.PARALLEL_GAP_X) + C.NODE_W / 2;
        const branchNodes: LayoutNode[] = [];
        let branchY = curY;

        for (const item of par.branches[bi]) {
          const h = getNodeHeight(item);
          branchNodes.push({
            kind: 'item',
            item,
            x: branchX,
            y: branchY,
            w: C.NODE_W,
            h,
          });
          branchY += h + C.GAP_Y;
        }

        layoutBranches.push(branchNodes);
        const branchHeight = branchY - curY;
        if (branchHeight > maxBranchHeight) maxBranchHeight = branchHeight;
      }

      const barBottomY = curY + maxBranchHeight;
      const totalH = barBottomY - barTopY + C.PARALLEL_BAR_H;

      elements.push({
        kind: 'parallel',
        parallel: par,
        x: centerX,
        y: barTopY,
        w: totalBranchWidth,
        h: totalH,
        branches: layoutBranches,
        barTopY,
        barBottomY,
      });

      curY = barBottomY + C.PARALLEL_BAR_H + C.GAP_Y;
      if (totalBranchWidth + C.MARGIN_X * 2 > maxWidth) {
        maxWidth = totalBranchWidth + C.MARGIN_X * 2;
      }
    } else {
      // 通常ノード
      const item = step as FlowchartItem;
      const h = getNodeHeight(item);
      elements.push({
        kind: 'item',
        item,
        x: centerX,
        y: curY,
        w: C.NODE_W,
        h,
      });

      // decision で branchNo がある場合、ループバック分の右側余白を考慮
      if (item.type === 'decision' && item.branchNo) {
        const neededWidth = C.NODE_W + C.MARGIN_X * 2 + C.LOOP_OFFSET_X + C.NODE_W / 2 + 40;
        if (neededWidth > maxWidth) maxWidth = neededWidth;
      }

      curY += h + C.GAP_Y;
    }
  }

  curY += C.MARGIN_BOTTOM - C.GAP_Y; // 最後のGAPを調整
  return { elements, totalWidth: maxWidth, totalHeight: curY };
}

// === SVGノード描画 ===
function renderNode(node: LayoutNode, key: string): JSX.Element[] {
  const { item, x, y, w, h } = node;
  const elems: JSX.Element[] = [];

  // deviceId付きラベル構築
  let fullLabel = item.label;
  if (item.deviceId) {
    fullLabel = `【${item.deviceId}】${item.label}`;
  }
  const lines = splitText(fullLabel, C.LINE_CHARS);
  const textStartY = y + h / 2 - ((lines.length - 1) * C.LINE_HEIGHT) / 2;

  switch (item.type) {
    case 'start':
    case 'end': {
      // 角丸楕円
      elems.push(
        <rect
          key={`${key}-shape`}
          x={x - w / 2}
          y={y}
          width={w}
          height={h}
          rx={h / 2}
          ry={h / 2}
          fill={C.FILL_START}
          stroke={C.STROKE}
          strokeWidth={1.5}
        />
      );
      break;
    }
    case 'process': {
      // 角丸なし四角
      elems.push(
        <rect
          key={`${key}-shape`}
          x={x - w / 2}
          y={y}
          width={w}
          height={h}
          fill={C.FILL_BG}
          stroke={C.STROKE}
          strokeWidth={1.5}
        />
      );
      break;
    }
    case 'decision': {
      // 菱形（4点のpath）
      const cx = x;
      const cy = y + h / 2;
      const hw = w / 2;
      const hh = h / 2;
      elems.push(
        <path
          key={`${key}-shape`}
          d={`M ${cx} ${cy - hh} L ${cx + hw} ${cy} L ${cx} ${cy + hh} L ${cx - hw} ${cy} Z`}
          fill={C.FILL_DECISION}
          stroke={C.STROKE}
          strokeWidth={1.5}
        />
      );
      break;
    }
    case 'subprocess': {
      // 二重枠の四角
      const inset = 4;
      elems.push(
        <rect
          key={`${key}-outer`}
          x={x - w / 2}
          y={y}
          width={w}
          height={h}
          fill={C.FILL_SUBPROCESS}
          stroke={C.STROKE}
          strokeWidth={1.5}
        />
      );
      elems.push(
        <rect
          key={`${key}-inner`}
          x={x - w / 2 + inset}
          y={y + inset}
          width={w - inset * 2}
          height={h - inset * 2}
          fill="none"
          stroke={C.STROKE}
          strokeWidth={1}
        />
      );
      break;
    }
  }

  // テキスト描画
  elems.push(
    <text
      key={`${key}-text`}
      x={x}
      y={textStartY}
      textAnchor="middle"
      dominantBaseline="central"
      fontFamily="sans-serif"
      fontSize={C.FONT_SIZE}
      fill={C.STROKE}
    >
      {lines.map((line, i) => (
        <tspan key={i} x={x} dy={i === 0 ? 0 : C.LINE_HEIGHT}>
          {line}
        </tspan>
      ))}
    </text>
  );

  // description（ノード下部に小さく表示）
  if (item.description) {
    const descLines = splitText(item.description, C.LINE_CHARS + 4);
    elems.push(
      <text
        key={`${key}-desc`}
        x={x}
        y={y + h + 12}
        textAnchor="middle"
        dominantBaseline="central"
        fontFamily="sans-serif"
        fontSize={10}
        fill="#666666"
      >
        {descLines.map((line, i) => (
          <tspan key={i} x={x} dy={i === 0 ? 0 : 13}>
            {line}
          </tspan>
        ))}
      </text>
    );
  }

  return elems;
}

// === 矢印（直線）描画 ===
function renderArrow(
  x1: number, y1: number,
  x2: number, y2: number,
  key: string,
  markerId: string
): JSX.Element {
  return (
    <line
      key={key}
      x1={x1} y1={y1}
      x2={x2} y2={y2}
      stroke={C.STROKE}
      strokeWidth={1.5}
      markerEnd={`url(#${markerId})`}
    />
  );
}

// === 直角パス（折れ線）描画 ===
function renderPathArrow(
  points: [number, number][],
  key: string,
  markerId: string
): JSX.Element {
  const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0]} ${p[1]}`).join(' ');
  return (
    <path
      key={key}
      d={d}
      fill="none"
      stroke={C.STROKE}
      strokeWidth={1.5}
      markerEnd={`url(#${markerId})`}
    />
  );
}

// === メインコンポーネント ===
export default function FlowchartRenderer({ steps, title }: Props) {
  const { svgContent, svgWidth, svgHeight } = useMemo(() => {
    if (!steps || steps.length === 0) {
      return { svgContent: null, svgWidth: 0, svgHeight: 0 };
    }

    // 仮のcenterXで一度計算してから幅を確定
    const preliminary = computeLayout(steps, 300);
    const centerX = preliminary.totalWidth / 2;
    const { elements, totalWidth, totalHeight } = computeLayout(steps, centerX);

    const markerId = 'flowchart-arrowhead';
    const content: JSX.Element[] = [];

    // マーカー定義
    content.push(
      <defs key="defs">
        <marker
          id={markerId}
          markerWidth={C.ARROW_SIZE}
          markerHeight={C.ARROW_SIZE}
          refX={C.ARROW_SIZE}
          refY={C.ARROW_SIZE / 2}
          orient="auto"
          markerUnits="userSpaceOnUse"
        >
          <path
            d={`M 0 0 L ${C.ARROW_SIZE} ${C.ARROW_SIZE / 2} L 0 ${C.ARROW_SIZE} Z`}
            fill={C.STROKE}
          />
        </marker>
      </defs>
    );

    // 白背景
    content.push(
      <rect key="bg" x={0} y={0} width={totalWidth} height={totalHeight} fill={C.FILL_BG} />
    );

    // ノード描画
    for (let i = 0; i < elements.length; i++) {
      const el = elements[i];

      if (el.kind === 'item') {
        content.push(...renderNode(el, `node-${i}`));
      } else if (el.kind === 'parallel') {
        const par = el;

        // 上部太い横線
        const barLeft = par.x - par.w / 2;
        const barRight = par.x + par.w / 2;
        content.push(
          <rect
            key={`par-${i}-top-bar`}
            x={barLeft}
            y={par.barTopY}
            width={par.w}
            height={C.PARALLEL_BAR_H}
            fill={C.STROKE}
          />
        );

        // 各ブランチのノード
        for (let bi = 0; bi < par.branches.length; bi++) {
          const branch = par.branches[bi];
          for (let ni = 0; ni < branch.length; ni++) {
            content.push(...renderNode(branch[ni], `par-${i}-b${bi}-n${ni}`));

            // ブランチ内ノード間の矢印
            if (ni > 0) {
              const prev = branch[ni - 1];
              const cur = branch[ni];
              content.push(
                renderArrow(
                  prev.x, prev.y + prev.h,
                  cur.x, cur.y,
                  `par-${i}-b${bi}-arrow-${ni}`,
                  markerId
                )
              );
            }
          }

          // 上部バーからブランチ最初のノードへの矢印
          if (branch.length > 0) {
            const first = branch[0];
            content.push(
              renderArrow(
                first.x, par.barTopY + C.PARALLEL_BAR_H,
                first.x, first.y,
                `par-${i}-b${bi}-from-bar`,
                markerId
              )
            );
          }

          // ブランチ最後のノードから下部バーへの線
          if (branch.length > 0) {
            const last = branch[branch.length - 1];
            content.push(
              <line
                key={`par-${i}-b${bi}-to-bar`}
                x1={last.x} y1={last.y + last.h}
                x2={last.x} y2={par.barBottomY}
                stroke={C.STROKE}
                strokeWidth={1.5}
              />
            );
          }
        }

        // 下部太い横線
        content.push(
          <rect
            key={`par-${i}-bottom-bar`}
            x={barLeft}
            y={par.barBottomY}
            width={par.w}
            height={C.PARALLEL_BAR_H}
            fill={C.STROKE}
          />
        );
      }
    }

    // ノード間の接続矢印（トップレベル）
    for (let i = 0; i < elements.length - 1; i++) {
      const cur = elements[i];
      const next = elements[i + 1];

      // 現在ノードの下部Y座標
      let fromX: number;
      let fromY: number;
      if (cur.kind === 'item') {
        fromX = cur.x;
        fromY = cur.y + cur.h;
      } else {
        fromX = cur.x;
        fromY = cur.barBottomY + C.PARALLEL_BAR_H;
      }

      // 次ノードの上部Y座標
      let toX: number;
      let toY: number;
      if (next.kind === 'item') {
        toX = next.x;
        toY = next.y;
      } else {
        toX = next.x;
        toY = next.barTopY;
      }

      // decision の branchYes ラベル
      if (cur.kind === 'item' && cur.item.type === 'decision') {
        const label = cur.item.branchYes || 'Yes';
        content.push(
          <text
            key={`arrow-label-yes-${i}`}
            x={fromX + 8}
            y={fromY + 14}
            fontFamily="sans-serif"
            fontSize={C.BRANCH_LABEL_SIZE}
            fill="#008800"
          >
            {label}
          </text>
        );
      }

      content.push(
        renderArrow(fromX, fromY, toX, toY, `conn-arrow-${i}`, markerId)
      );

      // decision の branchNo ループバック矢印
      if (cur.kind === 'item' && cur.item.type === 'decision' && cur.item.branchNo) {
        const cx = cur.x;
        const cy = cur.y + cur.h / 2;
        const rightEdge = cx + C.NODE_W / 2;
        const loopX = rightEdge + C.LOOP_OFFSET_X;

        // 右端から右へ、上へ戻るループ
        const loopTopY = cur.y - C.GAP_Y / 2;

        // ラベル
        content.push(
          <text
            key={`arrow-label-no-${i}`}
            x={rightEdge + 6}
            y={cy - 6}
            fontFamily="sans-serif"
            fontSize={C.BRANCH_LABEL_SIZE}
            fill="#cc0000"
          >
            {cur.item.branchNo}
          </text>
        );

        // ループパス：右→上→左へ戻る（矢頭は上向き終端）
        content.push(
          <path
            key={`loop-${i}`}
            d={`M ${rightEdge} ${cy} L ${loopX} ${cy} L ${loopX} ${loopTopY} L ${cx} ${loopTopY} L ${cx} ${cur.y}`}
            fill="none"
            stroke={C.STROKE}
            strokeWidth={1.5}
            markerEnd={`url(#${markerId})`}
          />
        );
      }
    }

    return { svgContent: content, svgWidth: totalWidth, svgHeight: totalHeight };
  }, [steps]);

  if (!steps || steps.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-dark-border overflow-hidden">
      {/* タイトルバー（LadderDiagramRendererと同じスタイル） */}
      <div className="flex items-center gap-2 px-4 py-2 bg-dark-hover border-b border-dark-border">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect x="3" y="1" width="10" height="4" rx="1" stroke="currentColor" strokeWidth="1.2" className="text-blue-400" />
          <rect x="3" y="11" width="10" height="4" rx="1" stroke="currentColor" strokeWidth="1.2" className="text-blue-400" />
          <path d="M 5 6 L 5 10 M 11 6 L 11 10" stroke="currentColor" strokeWidth="1.2" className="text-blue-400" />
          <line x1="8" y1="5" x2="8" y2="11" stroke="currentColor" strokeWidth="1.2" className="text-blue-400" />
        </svg>
        <span className="text-sm font-medium text-dark-text">
          {title || 'フローチャート'}
        </span>
      </div>

      {/* SVG本体（白背景） */}
      <div className="overflow-x-auto bg-white">
        <svg
          width={svgWidth}
          height={svgHeight}
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          xmlns="http://www.w3.org/2000/svg"
          style={{ display: 'block', minWidth: svgWidth }}
        >
          {svgContent}
        </svg>
      </div>
    </div>
  );
}
