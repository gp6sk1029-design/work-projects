# -*- coding: utf-8 -*-
"""変換したDXFが図面として妥当かを検証する。

・元図面とDXFの件数・ファイル名の対応
・中身が空／要素が極端に少ないDXFの検出

使い方:
    python verify_dxf.py --src "<図面フォルダ>" --out "<DXFフォルダ>"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-entities", type=int, default=20)
    a = ap.parse_args()
    a.src, a.out = fix_path(a.src), fix_path(a.out)
    for label, d in (("--src", a.src), ("--out", a.out)):
        if not os.path.isdir(d):
            print(f"NG: {label} のフォルダが見つかりません: {d}")
            print('   ヒント: UNCパスは "//nas-ime5/共有名/..." 形式で渡してください。')
            return 1

    src = sorted(os.path.splitext(f)[0] for f in os.listdir(a.src)
                 if f.lower().endswith(".slddrw"))
    dxf = sorted(os.path.splitext(f)[0] for f in os.listdir(a.out)
                 if f.lower().endswith(".dxf"))
    print(f"元図面 {len(src)}件 / DXF {len(dxf)}件")
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
    return 0 if not (missing or bad) else 1


if __name__ == "__main__":
    sys.exit(main())
