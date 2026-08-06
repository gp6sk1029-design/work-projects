# -*- coding: utf-8 -*-
"""図面PDF（CAD出力・テキスト付き）から 図番／品名／材質／数量 を抽出する。

表題欄は縦書きで、ラベル列のすぐ左に値が入る構造を利用する。
対称品は QTY欄が「上記」等になり、図中に
「数量：本図面品/図面対称品を各N個⇒計M個」と注記されるため、それを解釈する。

使い方:
    python parse_drawing_pdf.py <図面フォルダ> [-o 出力.json]

出力JSON（注文書入力スクリプトへそのまま渡せる形）:
    [{"katashiki": "3089-100-15A",
      "hinmei": "センサブラケット 本図面品/図面対称 各2個",
      "qty": 4, "tanka": null, "noki": "",
      "_name": "センサブラケット", "_material": "SUS", "_sym": true}, ...]
"""
import sys, os, re, glob, json, argparse

sys.stdout.reconfigure(encoding="utf-8")
import fitz


def field_value(words, labels):
    """ラベル語群のy範囲に『中心が入る』左隣の単語を連結して返す"""
    tgt = [w for w in words if w[4] in labels]
    if not tgt:
        return ""
    y0, y1 = min(w[1] for w in tgt), max(w[3] for w in tgt)
    lx = min(w[0] for w in tgt)
    c = [w for w in words
         if w[2] <= lx + 1 and w[0] > lx - 40
         and y0 <= (w[1] + w[3]) / 2 <= y1]
    c.sort(key=lambda w: w[1])
    return " ".join(w[4] for w in c).strip()


def parse_one(path):
    pg = fitz.open(path)[0]
    words, text = pg.get_text("words"), pg.get_text()
    fname = os.path.basename(path)
    katashiki = fname.split()[0]                       # ファイル名先頭＝図番

    # PART NAME 欄には他行の値が混ざるため、最後のトークンを品名とみなす
    name_field = field_value(words, {"PART", "NAME"})
    name = name_field.split()[-1] if name_field else ""
    material_field = field_value(words, {"MATERIAL"})
    material = material_field.split()[0] if material_field else ""
    qty_raw = field_value(words, {"QTY"})

    note = ""
    for line in text.splitlines():
        if "対称" in line and "個" in line:
            note = line.strip()
            break
    each = total = None
    if note:
        m = re.search(r"各\s*(\d+)\s*個", note)
        each = int(m.group(1)) if m else None
        m = re.search(r"計\s*(\d+)\s*個", note)
        total = int(m.group(1)) if m else None

    if total:                                          # 対称品
        qty = total
        hinmei = f"{name} 本図面品/図面対称 各{each}個"
    else:
        m = re.fullmatch(r"\d+", qty_raw)
        qty = int(m.group()) if m else None
        hinmei = name
    return {
        "katashiki": katashiki, "hinmei": hinmei, "qty": qty, "tanka": None, "noki": "",
        "_file": fname, "_name": name, "_material": material,
        "_qty_raw": qty_raw, "_sym": bool(total), "_each": each, "_note": note,
        "_fname_name": " ".join(fname.split()[1:]).split(" - ")[0],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.folder, "*.pdf")))
    if not files:
        print("PDFが見つかりません:", a.folder)
        return 1
    rows = [parse_one(p) for p in files]

    print(f"{len(rows)}件（対称品 {sum(1 for r in rows if r['_sym'])}件）\n")
    print(f"{'図番':<16}{'品名':<34}{'材質':<9}{'数量':>4}  {'対称'}")
    for r in rows:
        print(f"{r['katashiki']:<16}{r['hinmei']:<34}{r['_material']:<9}"
              f"{str(r['qty']):>4}  {'○' if r['_sym'] else ''}")

    bad = [r for r in rows if not r["qty"]]
    if bad:
        print("\n★数量を判定できなかった図面（要目視）:")
        for r in bad:
            print(f"  {r['katashiki']} {r['_name']}: QTY='{r['_qty_raw']}' 注記='{r['_note']}'")

    diff = [r for r in rows if r["_name"] != r["_fname_name"]]
    if diff:
        print("\n★図面の品名とファイル名が違う（図面側を採用しています。要確認）:")
        for r in diff:
            print(f"  {r['katashiki']}: 図面='{r['_name']}' / ファイル名='{r['_fname_name']}'")

    out = a.out or os.path.join(os.environ.get("TEMP", "."), "drawing_items.json")
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n保存:", out)
    print(f"合計数量: {sum(r['qty'] or 0 for r in rows)} 個")
    return 0


if __name__ == "__main__":
    sys.exit(main())
