# -*- coding: utf-8 -*-
"""変換したDXF／PDFが図面として妥当かを検証する。

・元図面と出力の件数・ファイル名の対応
・中身が空／要素が極端に少ないDXFの検出
・PDFの用紙サイズと線の本数の検出
  （SolidWorks標準のPDF書き出しは寸法線・枠が抜けて「文字だけ」になる。
    線が極端に少ないPDFはこれを疑う）

使い方:
    python verify_dxf.py --src "<図面フォルダ>" --out "<出力フォルダ>"
    python verify_dxf.py --src "..." --out "..." --format pdf   # PDFだけ検証
"""
import sys, os, re, argparse
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

ENT = re.compile(
    r"^\s*0\s*\r?\n\s*(LINE|CIRCLE|ARC|LWPOLYLINE|POLYLINE|TEXT|MTEXT|DIMENSION|INSERT|SOLID|SPLINE|ELLIPSE|POINT)\s*$",
    re.M)


def fix_path(p):
    """シェルで潰れたUNCパスを復元（\\nas→\\\\nas、//nas→\\\\nas）"""
    if not p:
        return p
    p = p.replace("/", "\\") if p.startswith("//") else p
    if p.startswith("\\") and not p.startswith("\\\\"):
        p = "\\" + p
    return p


def verify_pdf(src_names, outdir, min_paths):
    """PDFの用紙サイズ・線の本数を検査する。戻り値: 問題があればTrue"""
    try:
        import fitz
    except ImportError:
        print("\n[PDF検証] PyMuPDF(fitz)が入っていないため省略します（pip install pymupdf）")
        return False

    pdfs = sorted(f for f in os.listdir(outdir) if f.lower().endswith(".pdf"))
    print(f"\n=== PDF検証 ===\n元図面 {len(src_names)}件 / PDF {len(pdfs)}件")
    missing = [s for s in src_names if s not in [os.path.splitext(p)[0] for p in pdfs]]
    print("  PDFが無い図面:", missing if missing else "なし ✅")

    thin, raster, sizes = [], [], Counter()
    for f in pdfs:
        try:
            d = fitz.open(os.path.join(outdir, f))
            pg = d[0]
            lines = sum(len(d[i].get_drawings()) for i in range(d.page_count))
            imgs = sum(len(d[i].get_images()) for i in range(d.page_count))
            sizes[f"{round(pg.rect.width*25.4/72)}x{round(pg.rect.height*25.4/72)}mm"] += 1
            if lines < min_paths:
                # 画像があるなら「ページ全体がラスタ化された図面」。
                # シェーディングされた3Dビューを含む図面を印刷すると必ずこうなる（欠落ではない）
                (raster if imgs else thin).append((f, lines))
            d.close()
        except Exception as e:
            thin.append((f, f"開けない（使用中の可能性）: {e}"))
    print("  用紙サイズ:", " / ".join(f"{k} {v}件" for k, v in sizes.most_common()))
    if thin:
        print(f"  ⚠️ 線が{min_paths}本未満で画像も無いPDF（寸法線・枠の欠落を疑う）:")
        for f, n in thin:
            print(f"    {f}: {n}")
    else:
        print(f"  線の欠落: なし ✅")
    if raster:
        print(f"  ℹ️ ページ全体がラスタ画像のPDF {len(raster)}件"
              f"（シェーディング3Dビューを含む図面。内容は欠けていないがファイルは大きい）:")
        for f, _ in raster:
            print(f"    {f}")
    return bool(missing or thin)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-entities", type=int, default=20)
    ap.add_argument("--format", default="dxf,pdf",
                    help="検証する形式（dxf / pdf / dxf,pdf）")
    ap.add_argument("--min-paths", type=int, default=50,
                    help="PDF1件あたりの線の最低本数（これ未満は欠落を疑う）")
    a = ap.parse_args()
    formats = [f.strip().lower() for f in a.format.split(",") if f.strip()]
    a.src, a.out = fix_path(a.src), fix_path(a.out)
    for label, d in (("--src", a.src), ("--out", a.out)):
        if not os.path.isdir(d):
            print(f"NG: {label} のフォルダが見つかりません: {d}")
            print('   ヒント: UNCパスは "//nas-ime5/共有名/..." 形式で渡してください。')
            return 1

    src = sorted(os.path.splitext(f)[0] for f in os.listdir(a.src)
                 if f.lower().endswith(".slddrw"))
    ng = False

    if "dxf" in formats:
        dxf = sorted(os.path.splitext(f)[0] for f in os.listdir(a.out)
                     if f.lower().endswith(".dxf"))
        print(f"=== DXF検証 ===\n元図面 {len(src)}件 / DXF {len(dxf)}件")
        missing = [s for s in src if s not in dxf]
        print("  変換されていない図面:", missing if missing else "なし ✅")

        bad, small, total = [], [], 0
        for f in sorted(os.listdir(a.out)):
            if not f.lower().endswith(".dxf"):
                continue
            p = os.path.join(a.out, f)
            txt = open(p, "rb").read().decode("cp932", errors="replace")
            n = sum(Counter(ENT.findall(txt)).values())
            total += n
            if n == 0:
                bad.append(f)
            elif n < a.min_entities:
                small.append((f, n))

        print(f"\n図形要素の合計: {total:,} 個（平均 {total//max(len(dxf),1)} 個/図面）")
        print("  中身が空のDXF:", bad if bad else "なし ✅")
        if small:
            print(f"  要素が{a.min_entities}未満の図面（要目視）:")
            for f, n in small:
                print(f"    {f}: {n}個")
        else:
            print("  要素が極端に少ない図面: なし ✅")

        sizes = [(os.path.getsize(os.path.join(a.out, f)), f)
                 for f in os.listdir(a.out) if f.lower().endswith(".dxf")]
        if sizes:
            sizes.sort()
            print(f"\nサイズ: 最小 {sizes[0][0]:,}B ({sizes[0][1]})")
            print(f"        最大 {sizes[-1][0]:,}B ({sizes[-1][1]})")
            print(f"        合計 {sum(s for s, _ in sizes):,}B")
        ng = ng or bool(missing or bad)

    if "pdf" in formats:
        ng = verify_pdf(src, a.out, a.min_paths) or ng

    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
