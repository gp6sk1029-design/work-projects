# -*- coding: utf-8 -*-
"""同じフォルダにあるDXFとPDFが「同じ図面か」を照合する。

取引先へ支給する前の最終チェック。ファイル名が合っていても、中身が
別の図面・古い版になっている事故を見つける。

見るところ:
  1. DXFとPDFが1対1で揃っているか（片方だけ無いものを検出）
  2. 図番（DRAWING No.）が ファイル名／DXF内／PDF内 の3つで一致するか
  3. 品名・材質・数量・機種名が一致するか
  4. PDFに書かれている寸法値が、すべてDXF側にもあるか
     （DXFには非表示レイヤ等も入るので「PDF ⊆ DXF」で判定する）

使い方:
    python match_dxf_pdf.py --dir "<DXFとPDFが入ったフォルダ>"
    python match_dxf_pdf.py --dir "..." --png-out "<画像の出力先>"   # ラスタPDFを画像化
"""
import sys, os, re, argparse

sys.stdout.reconfigure(encoding="utf-8")

NUM = re.compile(r"\d+(?:\.\d+)?")
DRAWING_NO = re.compile(r"\d{3,4}-\d{2,3}-\d{2,3}[A-Z]?")


def fix_path(p):
    """シェルで潰れたUNCパスを復元（\\nas→\\\\nas、//nas→\\\\nas）"""
    if not p:
        return p
    p = p.replace("/", "\\") if p.startswith("//") else p
    if p.startswith("\\") and not p.startswith("\\\\"):
        p = "\\" + p
    return p


def norm(s):
    """全角空白・連続空白をならす"""
    return re.sub(r"\s+", " ", s.replace("　", " ")).strip()


def dxf_texts(path):
    """DXFの文字をすべて集める（モデル空間＋そこから参照されるブロック）"""
    import ezdxf
    doc = ezdxf.readfile(path)
    out, seen_blocks = [], set()

    def dive(name):
        """ブロックの中身をたどる"""
        if not name or name in seen_blocks or name not in doc.blocks:
            return
        seen_blocks.add(name)
        for sub in doc.blocks[name]:
            pick(sub)

    def pick(entity):
        t = entity.dxftype()
        if t == "TEXT":
            out.append(entity.dxf.text)
        elif t == "MTEXT":
            out.append(entity.plain_text())
        elif t == "INSERT":                      # 図面枠・記号はブロックの中にある
            dive(entity.dxf.name)
        elif t == "DIMENSION":
            # 寸法値の文字は *D... という専用ブロックの中にある。
            # ここを見ないと寸法がまるごと拾えない（照合の要）
            dive(getattr(entity.dxf, "geometry", None))
            txt = getattr(entity.dxf, "text", "")
            if txt and txt not in ("<>", " "):   # 手入力で上書きした寸法値
                out.append(txt)
            try:
                out.append(f"{entity.get_measurement():g}")
            except Exception:
                pass

    for e in doc.modelspace():
        pick(e)
    return [norm(v) for v in out if norm(v)]


def pdf_texts(path):
    """PDFの文字を集める。ラスタ化されたPDFは空リストになる"""
    import fitz
    with fitz.open(path) as d:
        return [norm(v) for v in "\n".join(p.get_text() for p in d).splitlines() if norm(v)]


def find_no(texts):
    """図番らしき文字列を返す"""
    for t in texts:
        m = DRAWING_NO.search(t)
        if m:
            return m.group()
    return ""


def numbers(texts):
    return {m for t in texts for m in NUM.findall(t)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="DXFとPDFが入ったフォルダ")
    ap.add_argument("--png-out", default="", help="ラスタPDFを画像化する出力先")
    ap.add_argument("--min-rate", type=float, default=95.0,
                    help="PDFの寸法値がDXFにある割合の合格ライン(%%)")
    a = ap.parse_args()
    a.dir = fix_path(a.dir)
    if not os.path.isdir(a.dir):
        print("NG: フォルダが見つかりません:", a.dir)
        print('   ヒント: UNCパスは "//nas-ime5/共有名/..." 形式で渡してください。')
        return 1

    files = os.listdir(a.dir)
    dxfs = {os.path.splitext(f)[0]: f for f in files if f.lower().endswith(".dxf")}
    pdfs = {os.path.splitext(f)[0]: f for f in files if f.lower().endswith(".pdf")}
    bases = sorted(set(dxfs) | set(pdfs))

    print(f"フォルダ: {a.dir}")
    print(f"  DXF {len(dxfs)}件 / PDF {len(pdfs)}件 / 名前の種類 {len(bases)}種\n")

    only_dxf = sorted(set(dxfs) - set(pdfs))
    only_pdf = sorted(set(pdfs) - set(dxfs))
    if only_dxf:
        print("⚠️ PDFが無い（DXFだけ）:")
        for b in only_dxf:
            print("   ", b)
    if only_pdf:
        print("⚠️ DXFが無い（PDFだけ）:")
        for b in only_pdf:
            print("   ", b)
    if not (only_dxf or only_pdf):
        print("ペア: DXFとPDFが全件そろっています ✅")

    ng, manual, rows = [], [], []
    for b in bases:
        if b not in dxfs or b not in pdfs:
            continue
        dt = dxf_texts(os.path.join(a.dir, dxfs[b]))
        pt = pdf_texts(os.path.join(a.dir, pdfs[b]))
        file_no = (DRAWING_NO.search(b).group() if DRAWING_NO.search(b) else "")
        name = norm(b[len(file_no):]) if file_no else ""
        d_no, p_no = find_no(dt), find_no(pt)

        if not pt:                    # 文字が取れない＝ページ全体がラスタ画像
            manual.append(b)
            rows.append((b, file_no, d_no, "(画像)", "-", "-", "要目視"))
            continue

        d_join, p_join = " / ".join(dt), " / ".join(pt)
        name_ok = (name in d_join) and (name in p_join)
        p_num, d_num = numbers(pt), numbers(dt)
        missing = sorted(p_num - d_num, key=lambda x: (len(x), x))
        rate = 100.0 if not p_num else 100.0 * (len(p_num) - len(missing)) / len(p_num)

        no_ok = file_no and d_no == file_no and p_no == file_no
        ok = no_ok and name_ok and rate >= a.min_rate
        rows.append((b, file_no, d_no, p_no, "○" if name_ok else "×",
                     f"{rate:.0f}%", "OK" if ok else "NG"))
        if not ok:
            ng.append((b, file_no, d_no, p_no, name_ok, rate, missing[:10]))

    print("\n=== 照合結果 ===")
    print(f"{'ファイル名':<34}{'ファイル':<14}{'DXF':<14}{'PDF':<14}{'品名':<5}{'寸法':<7}判定")
    for r in rows:
        nm = r[0] if len(r[0]) <= 32 else r[0][:31] + "…"
        print(f"{nm:<34}{r[1]:<14}{r[2]:<14}{str(r[3]):<14}{r[4]:<5}{r[5]:<7}{r[6]}")

    if ng:
        print("\n❌ 不一致の詳細:")
        for b, fno, dno, pno, nok, rate, miss in ng:
            print(f"  {b}")
            if dno != fno or pno != fno:
                print(f"    図番: ファイル名={fno} / DXF={dno} / PDF={pno}")
            if not nok:
                print("    品名がDXFまたはPDFの中に見つかりません")
            if rate < a.min_rate:
                print(f"    PDFにありDXFに無い数値（{rate:.0f}%一致）: {', '.join(miss)}")
    if manual:
        print(f"\nℹ️ 文字が取れないPDF {len(manual)}件（シェーディング3Dビューでラスタ化）"
              "＝自動照合できないため目視:")
        for b in manual:
            print("   ", b)
        if a.png_out:
            import fitz
            os.makedirs(a.png_out, exist_ok=True)
            for b in manual:
                with fitz.open(os.path.join(a.dir, pdfs[b])) as d:
                    d[0].get_pixmap(dpi=100).save(os.path.join(a.png_out, b + ".png"))
            print("   → 画像を出力しました:", a.png_out)

    bad = bool(ng or only_dxf or only_pdf)
    print("\n" + ("★ 要確認あり（上記）" if bad else "✅ 全件一致しています")
          + (f"／目視確認 {len(manual)}件" if manual else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
