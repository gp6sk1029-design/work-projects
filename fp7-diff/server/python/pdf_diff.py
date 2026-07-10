"""
FP7 Diff: PDFラダー図 視覚比較エンジン
  入力: 2つのPDFファイル + 出力ディレクトリ
  出力: JSON（stdoutに）＋ ページ画像PNG（出力ディレクトリに）

処理:
  1. 各PDFの全ページを150dpiでPNG化
  2. pHash(8x8)で各ページの知覚ハッシュを計算
  3. AとBのページを類似度でマッチング（ハミング距離≦threshold）
  4. マッチした対だけOpenCVでピクセル差分→矩形検出
  5. 結果をJSONで stdout 出力

stdoutはJSONのみ、ログは stderr に分離（Windows cp932対策）
"""
import argparse
import json
import logging
import sys
import os
from pathlib import Path
from typing import Optional

import fitz                          # PyMuPDF
import imagehash
import numpy as np
from PIL import Image
import cv2

# stdoutはバイト書き込み、ログはstderr
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    stream=sys.stderr,
)
log = logging.getLogger('pdf_diff')

# 設定
DPI = 220                       # PNG化解像度（拡大しても文字潰れない高解像度）
HASH_SIZE = 8                   # pHashのサイズ
MATCH_HAMMING_THRESHOLD = 8     # ハミング距離≦これなら同一/類似ページ
EXACT_HAMMING_THRESHOLD = 2     # ≦これなら完全一致扱い（差分検出スキップ）
DIFF_MIN_AREA = 200             # 差分矩形の最小面積（ノイズ除去）
DIFF_DILATE_KERNEL = 5          # 差分領域膨張カーネル

def render_pages(pdf_path: Path, out_dir: Path, prefix: str) -> list[dict]:
    """PDFをページ単位でPNG化し、pHashも一緒に計算"""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        # ヘッダのテキスト（PB名等）も抽出（後で対応付けヒントに使用）
        text = page.get_text() or ''

        # 150dpi でレンダリング
        zoom = DPI / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_path = out_dir / f'{prefix}_p{i+1:03d}.png'
        pix.save(str(img_path))

        # pHash
        with Image.open(img_path) as im:
            phash = str(imagehash.phash(im, hash_size=HASH_SIZE))
            w, h = im.size

        pages.append({
            'index': i,
            'pageNumber': i + 1,
            'filename': img_path.name,
            'phash': phash,
            'width': w,
            'height': h,
            'headerText': text[:200],
        })
    doc.close()
    return pages


def hamming(h1: str, h2: str) -> int:
    """16進文字列phash 同士のハミング距離"""
    return imagehash.hex_to_hash(h1) - imagehash.hex_to_hash(h2)


def match_pages(pages_a: list[dict], pages_b: list[dict]) -> list[dict]:
    """
    pHashで両側のページを対応付け
    戦略: Aの各ページについて、まだ使われていないBのページの中から
          ハミング距離が最小のものを選ぶ（距離が閾値超なら未対応）

    順序を尊重しつつ貪欲法でマッチング。
    """
    used_b = set()
    matches = []

    # 順序保持の貪欲マッチング: Aを順番に走査
    # まず厳密な完全一致を優先
    for a in pages_a:
        # 探索範囲を「現在位置の前後」に限定（順序維持）
        best_j = None
        best_dist = MATCH_HAMMING_THRESHOLD + 1
        for j, b in enumerate(pages_b):
            if j in used_b:
                continue
            d = hamming(a['phash'], b['phash'])
            if d < best_dist:
                best_dist = d
                best_j = j
        if best_j is not None and best_dist <= MATCH_HAMMING_THRESHOLD:
            used_b.add(best_j)
            matches.append({
                'aIndex': a['index'],
                'bIndex': best_j,
                'hamming': best_dist,
                'status': 'exact' if best_dist <= EXACT_HAMMING_THRESHOLD else 'similar',
            })
        else:
            matches.append({
                'aIndex': a['index'],
                'bIndex': None,
                'hamming': -1,
                'status': 'a_only',
            })

    # Bで未対応のページ
    for j, b in enumerate(pages_b):
        if j not in used_b:
            matches.append({
                'aIndex': None,
                'bIndex': j,
                'hamming': -1,
                'status': 'b_only',
            })

    return matches


def detect_pixel_diff(img_a_path: Path, img_b_path: Path, diff_out_path: Path) -> dict:
    """
    2つの画像の差分領域を検出
    - 画像をグレースケール化
    - サイズ揃える（小さい方に合わせる）
    - 差分→閾値→膨張→輪郭抽出→矩形リスト
    - 差分を赤枠でA画像に重ねた合成画像を diff_out_path に保存
    """
    img_a = cv2.imread(str(img_a_path))
    img_b = cv2.imread(str(img_b_path))
    if img_a is None or img_b is None:
        log.warning(f'画像読込失敗: {img_a_path}, {img_b_path}')
        return {'rects': [], 'totalArea': 0, 'changedRatio': 0.0}

    # サイズを揃える（小さい方に合わせる）
    h = min(img_a.shape[0], img_b.shape[0])
    w = min(img_a.shape[1], img_b.shape[1])
    img_a_r = cv2.resize(img_a, (w, h))
    img_b_r = cv2.resize(img_b, (w, h))

    gray_a = cv2.cvtColor(img_a_r, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b_r, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray_a, gray_b)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

    # ノイズ除去＋差分エリアを膨張させてまとめる
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (DIFF_DILATE_KERNEL, DIFF_DILATE_KERNEL))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    thresh = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects = []
    total_area = 0
    overlay = img_a_r.copy()
    overlay_b = img_b_r.copy()
    for c in contours:
        x, y, rw, rh = cv2.boundingRect(c)
        area = rw * rh
        if area < DIFF_MIN_AREA:
            continue
        total_area += area
        rects.append({'x': x, 'y': y, 'w': rw, 'h': rh})
        # 赤枠を描画
        cv2.rectangle(overlay, (x, y), (x + rw, y + rh), (0, 0, 255), 3)
        cv2.rectangle(overlay_b, (x, y), (x + rw, y + rh), (0, 0, 255), 3)

    # 差分入り画像を保存（A・B両方）
    diff_a_path = diff_out_path.parent / f'{diff_out_path.stem}_a.png'
    diff_b_path = diff_out_path.parent / f'{diff_out_path.stem}_b.png'
    cv2.imwrite(str(diff_a_path), overlay)
    cv2.imwrite(str(diff_b_path), overlay_b)

    changed_ratio = total_area / (w * h) if w > 0 and h > 0 else 0.0

    return {
        'rects': rects,
        'totalArea': total_area,
        'changedRatio': round(changed_ratio, 4),
        'diffImageA': diff_a_path.name,
        'diffImageB': diff_b_path.name,
    }


def main():
    parser = argparse.ArgumentParser(description='FP7 PDF ラダー図差分エンジン')
    parser.add_argument('--pdf-a', required=True, type=Path, help='プロジェクトA PDF')
    parser.add_argument('--pdf-b', required=True, type=Path, help='プロジェクトB PDF')
    parser.add_argument('--out-dir', required=True, type=Path, help='出力ディレクトリ')
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info(f'PDF A をレンダリング: {args.pdf_a}')
    pages_a = render_pages(args.pdf_a, out_dir, 'a')
    log.info(f'  {len(pages_a)} ページ完了')

    log.info(f'PDF B をレンダリング: {args.pdf_b}')
    pages_b = render_pages(args.pdf_b, out_dir, 'b')
    log.info(f'  {len(pages_b)} ページ完了')

    log.info('ページ対応付け中（pHash）...')
    matches = match_pages(pages_a, pages_b)

    # 差分検出
    log.info(f'ピクセル差分検出中（{sum(1 for m in matches if m["status"] == "similar")} ページ）...')
    for m in matches:
        if m['status'] != 'similar':
            m['pixelDiff'] = None
            continue
        a_path = out_dir / pages_a[m['aIndex']]['filename']
        b_path = out_dir / pages_b[m['bIndex']]['filename']
        diff_path = out_dir / f'diff_{m["aIndex"]+1:03d}_vs_{m["bIndex"]+1:03d}.png'
        m['pixelDiff'] = detect_pixel_diff(a_path, b_path, diff_path)

    # 集計
    summary = {
        'pagesA': len(pages_a),
        'pagesB': len(pages_b),
        'exactMatches': sum(1 for m in matches if m['status'] == 'exact'),
        'similarMatches': sum(1 for m in matches if m['status'] == 'similar'),
        'onlyInA': sum(1 for m in matches if m['status'] == 'a_only'),
        'onlyInB': sum(1 for m in matches if m['status'] == 'b_only'),
    }
    log.info(f'集計: {summary}')

    result = {
        'pagesA': pages_a,
        'pagesB': pages_b,
        'matches': matches,
        'summary': summary,
    }

    # numpy型をPython標準型に変換するヘルパー
    def _default(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(f'JSON 非対応の型: {type(o)}')

    # JSONを stdout に出力（UTF-8 バイト直接書き込み）
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, default=_default).encode('utf-8'))


if __name__ == '__main__':
    main()
