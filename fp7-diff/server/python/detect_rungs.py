"""
プロトタイプ: PDFラダー図 ページ画像からラング境界を検出
目的: 1ページの画像からラング境界（水平線/コメント帯）を見つけて、ラング単位で切り出せるか検証

戦略:
  1. グレースケール変換
  2. 水平方向の投影プロファイル（各y座標の暗いピクセル数）
  3. コメント帯（薄黄色の背景）と水平区切り線（連続する暗ピクセル）を検出
  4. y座標を「境界候補」として整列
  5. 結果画像（赤線アノテーション）と各ラング切り出しを保存
"""
import argparse
import sys, io
import os
import logging
from pathlib import Path
import numpy as np
import cv2

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger('detect_rungs')


def detect_rung_boundaries(img_bgr: np.ndarray) -> tuple[list[int], dict]:
    """
    画像からラング境界のy座標を検出
    戻り値: (境界y座標リスト, デバッグ情報)
    """
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # === 戦略1: 黄色っぽいコメント帯を検出 ===
    # FPWIN GR7 のコメント行は薄い黄色〜ベージュ
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # 黄色〜薄ベージュ: H=20-40, S=20-200, V=180-255
    yellow_mask = cv2.inRange(hsv, (15, 20, 180), (45, 255, 255))
    # 水平方向に集計
    yellow_row_count = np.sum(yellow_mask > 0, axis=1)
    # 黄色ピクセルが画像幅の30%以上のy → コメント帯候補
    yellow_threshold = w * 0.30
    yellow_rows = np.where(yellow_row_count > yellow_threshold)[0]

    # 連続するyを結合してバンド区間化（[start, end]のリスト）
    yellow_bands = []
    if len(yellow_rows) > 0:
        current_start = yellow_rows[0]
        prev = yellow_rows[0]
        for y in yellow_rows[1:]:
            if y - prev > 3:
                yellow_bands.append((int(current_start), int(prev)))
                current_start = y
            prev = y
        yellow_bands.append((int(current_start), int(prev)))

    log.info(f'  黄色コメント帯: {len(yellow_bands)} 検出')

    # === 戦略2: 水平区切り線（横長の暗い線）を検出 ===
    # 暗い線: 各y座標で「全幅にわたって暗いピクセルが連続」なライン
    # まずカーネルで水平方向に強調
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 4, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    line_row_count = np.sum(horizontal_lines > 0, axis=1)
    line_threshold = w * 0.50
    line_rows = np.where(line_row_count > line_threshold)[0]
    line_ys: list[int] = []
    if len(line_rows) > 0:
        prev = line_rows[0]
        for y in line_rows[1:]:
            if y - prev > 3:
                line_ys.append(int(prev))
            prev = y
        line_ys.append(int(prev))
    log.info(f'  水平区切り線: {len(line_ys)} 検出')

    # === 境界候補を統合 ===
    boundaries = set()
    # コメント帯の「上端」を境界として採用（コメント帯=新しいラングの開始）
    for start, end in yellow_bands:
        boundaries.add(start)
    # 水平線も境界
    for y in line_ys:
        boundaries.add(y)

    # ソート＋近接マージ
    sorted_b = sorted(boundaries)
    merged: list[int] = []
    for y in sorted_b:
        if not merged or y - merged[-1] > 8:
            merged.append(y)

    # 画像端も境界に
    if not merged or merged[0] > 5:
        merged.insert(0, 0)
    if not merged or merged[-1] < h - 5:
        merged.append(h)

    debug = {
        'yellow_bands': yellow_bands,
        'line_ys': line_ys,
        'image_size': (w, h),
    }
    return merged, debug


def annotate_image(img_bgr: np.ndarray, boundaries: list[int], debug: dict, out_path: Path):
    """境界を赤線、コメント帯を半透明黄色で重ねた画像を保存"""
    canvas = img_bgr.copy()
    h, w = canvas.shape[:2]

    # コメント帯（黄色オーバーレイ）
    overlay = canvas.copy()
    for start, end in debug['yellow_bands']:
        cv2.rectangle(overlay, (0, start), (w, end), (0, 255, 255), -1)
    canvas = cv2.addWeighted(overlay, 0.18, canvas, 0.82, 0)

    # 境界線（赤）
    for y in boundaries:
        cv2.line(canvas, (0, y), (w, y), (0, 0, 255), 2)

    # ラング番号（青）
    for i in range(len(boundaries) - 1):
        y_mid = (boundaries[i] + boundaries[i + 1]) // 2
        cv2.putText(canvas, f'#{i}', (5, y_mid), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    cv2.imwrite(str(out_path), canvas)


def crop_rungs(img_bgr: np.ndarray, boundaries: list[int], out_dir: Path, prefix: str):
    """境界に従ってラング画像を切り出して保存"""
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(len(boundaries) - 1):
        y_start = boundaries[i]
        y_end = boundaries[i + 1]
        if y_end - y_start < 15:
            continue
        crop = img_bgr[y_start:y_end, :, :]
        cv2.imwrite(str(out_dir / f'{prefix}_rung{i:03d}.png'), crop)


def main():
    parser = argparse.ArgumentParser(description='プロトタイプ: ラング境界検出')
    parser.add_argument('--input', required=True, type=Path, help='入力PNG画像')
    parser.add_argument('--out-dir', required=True, type=Path, help='出力ディレクトリ')
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    img = cv2.imread(str(args.input))
    if img is None:
        log.error(f'画像読込失敗: {args.input}')
        sys.exit(1)

    log.info(f'入力: {args.input.name} {img.shape}')
    boundaries, debug = detect_rung_boundaries(img)
    log.info(f'検出されたラング数: {len(boundaries) - 1}')

    annotated = args.out_dir / f'{args.input.stem}_annotated.png'
    annotate_image(img, boundaries, debug, annotated)
    log.info(f'アノテーション画像: {annotated}')

    crop_dir = args.out_dir / f'{args.input.stem}_rungs'
    crop_rungs(img, boundaries, crop_dir, args.input.stem)
    n = len(list(crop_dir.glob('*.png')))
    log.info(f'切り出したラング: {n}枚 → {crop_dir}')

    print(f'OK: ラング数 {len(boundaries) - 1}')


if __name__ == '__main__':
    main()
