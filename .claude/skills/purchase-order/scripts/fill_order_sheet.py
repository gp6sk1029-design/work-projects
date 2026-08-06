# -*- coding: utf-8 -*-
"""明細JSONを注文書Excelの指定タブへ入力し、そのまま読み戻して全件照合する。

明細JSONの各要素:
    {"katashiki": 型式, "hinmei": 品名, "qty": 数量,
     "tanka": 単価 or null, "noki": 納期文字列（任意）}

使い方:
    python fill_order_sheet.py --xlsx 注文書.xlsx --sheet NTS --json items.json \
        [--start-page 5] [--date 2026/8/6] [--dry-run]

・金額列は既存の数式（=数量*単価）に任せる（触らない）
・単価が null の項目は単価欄を空のままにする
・--start-page は注文No.の末尾番号（例 U5 → 5）。省略時は最初の空きページ
"""
import sys, os, json, shutil, argparse, datetime

sys.stdout.reconfigure(encoding="utf-8")
import win32com.client

COLS = {"B": 2, "J": 10, "R": 18, "Z": 26, "AH": 34}
# (頁番号行, 明細開始, 明細終了, 合計行, 日付行)
BLOCKS = [(7, 16, 40, 41, 3), (52, 61, 85, 86, 48), (97, 106, 130, 131, 93)]
ROWS_PER_PAGE = 25
OFF_KATA, OFF_HINMEI, OFF_QTY, OFF_TANKA, OFF_NOKI = 0, 1, 3, 4, 6


def build_pages(ws_v):
    """(ページ番号, 型式列, 明細開始行, 合計行, 日付セル, 使用済みか) の一覧"""
    pages = []
    for prow, r0, r1, rsum, drow in BLOCKS:
        for cl, ci in COLS.items():
            pnum = ws_v.Cells(prow, ci + 1).Value
            if pnum is None:
                continue
            used = any(ws_v.Cells(r, ci).Value not in (None, "") for r in range(r0, r1 + 1))
            date_cell = f"{chr(ord(cl[0]) + 5) if len(cl) == 1 else 'A'}{drow}"
            # 日付セルは型式列+5（G/O/W/AE/AM）
            col_letter = ws_v.Cells(1, ci + 5).Address(True, True).split("$")[1]
            date_cell = f"{col_letter}{drow}"
            pages.append({"no": int(pnum), "col": ci, "r0": r0, "rsum": rsum,
                          "date": date_cell, "used": used})
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--start-page", type=int, default=None)
    ap.add_argument("--date", default=None, help="例 2026/8/6（文字列で渡すこと）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    path = os.path.abspath(a.xlsx)
    lock = os.path.join(os.path.dirname(path), "~$" + os.path.basename(path))
    if os.path.exists(lock):
        print("NG: Excelで開かれています。閉じてから実行してください。")
        return 1

    items = json.load(open(a.json, encoding="utf-8"))
    print(f"明細 {len(items)}件")

    bak = os.path.join(os.environ.get("TEMP", "."),
                       f"backup_{datetime.datetime.now():%Y%m%d_%H%M%S}_{os.path.basename(path)}")
    shutil.copy2(path, bak)
    print("バックアップ:", bak)

    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        wb = excel.Workbooks.Open(path)
        ws = wb.Worksheets(a.sheet)
        pages = build_pages(ws)
        if a.start_page:
            pages = [p for p in pages if p["no"] >= a.start_page]
        else:
            pages = [p for p in pages if not p["used"]] or pages
        need = -(-len(items) // ROWS_PER_PAGE)
        if len(pages) < need:
            print(f"NG: ページ不足（必要 {need} / 使える {len(pages)}）")
            wb.Close(SaveChanges=False)
            return 1
        print(f"入力先: ページ {pages[0]['no']} から {need} ページ使用")
        if a.dry_run:
            wb.Close(SaveChanges=False)
            return 0

        idx = 0
        for p in pages[:need]:
            chunk = items[idx: idx + ROWS_PER_PAGE]
            idx += ROWS_PER_PAGE
            for k, it in enumerate(chunk):
                r = p["r0"] + k
                ws.Cells(r, p["col"] + OFF_KATA).Value = it["katashiki"]
                ws.Cells(r, p["col"] + OFF_HINMEI).Value = it["hinmei"]
                ws.Cells(r, p["col"] + OFF_QTY).Value = it["qty"]
                if it.get("tanka") is not None:
                    ws.Cells(r, p["col"] + OFF_TANKA).Value = it["tanka"]
                if it.get("noki"):
                    ws.Cells(r, p["col"] + OFF_NOKI).Value = it["noki"]
            if a.date:
                ws.Range(p["date"]).Value = a.date        # 文字列で渡す（ずれ防止）
            print(f"  ページ{p['no']}: {len(chunk)}件")
        excel.CalculateFullRebuild()

        # 読み戻して全件照合
        print("\n=== 検証 ===")
        idx, ng, total = 0, 0, 0
        for p in pages[:need]:
            chunk = items[idx: idx + ROWS_PER_PAGE]
            idx += ROWS_PER_PAGE
            for k, it in enumerate(chunk):
                r = p["r0"] + k
                got = (ws.Cells(r, p["col"]).Value,
                       ws.Cells(r, p["col"] + OFF_HINMEI).Value,
                       ws.Cells(r, p["col"] + OFF_QTY).Value)
                exp = (it["katashiki"], it["hinmei"], it["qty"])
                if got != exp:
                    ng += 1
                    print(f"  ❌ ページ{p['no']}行{r}: 期待={exp} 実際={got}")
            s = ws.Cells(p["rsum"], p["col"] + 5).Value or 0
            total += s
            print(f"  ページ{p['no']}: 合計 {s:,.0f} 円")
        print(f"  不一致 {ng}件", "→ 全件一致 ✅" if ng == 0 else "★要修正")
        print(f"  総合計 = {total:,.0f} 円")
        exp_total = sum((it['qty'] or 0) * (it.get('tanka') or 0) for it in items)
        if exp_total:
            print(f"  明細から計算した合計 = {exp_total:,} 円",
                  "✅一致" if abs(total - exp_total) < 1 else "❌不一致")
        wb.Save()
        wb.Close(SaveChanges=False)
    finally:
        excel.Quit()
    print("\n保存しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
