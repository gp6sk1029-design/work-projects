# -*- coding: utf-8 -*-
"""実績ファイル → 会費収支管理テンプレートを生成する。

個人情報（氏名・区分・状況・備考・チェック）と金額実績を消去し、
数式・条件付き書式・ドロップダウン・会費テーブルはそのまま残す。

使い方:
    python make_template.py <元ファイル.xlsx> <出力テンプレート.xlsx>
※ 元ファイルはExcelで閉じておくこと（開いているとロックで失敗する）
"""
import sys, os, shutil

sys.stdout.reconfigure(encoding="utf-8")
import win32com.client

DATE_FMT = 'yyyy"年"m"月"d"日"'
FIRST, LAST = 7, 46  # 参加者行
xlValidateList = 3


def main(src, dst):
    src, dst = os.path.abspath(src), os.path.abspath(dst)
    lock = os.path.join(os.path.dirname(src), "~$" + os.path.basename(src))
    if os.path.exists(lock):
        print("NG: 元ファイルがExcelで開かれています。閉じてから再実行してください。")
        return 1
    shutil.copy2(src, dst)

    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        wb = excel.Workbooks.Open(dst)
        ws = wb.Worksheets("収支管理")
        wss = wb.Worksheets("設定")

        # ── ① 参加者データを消去（数式列 E/F/H/N/P は残す）──
        for col in ("C", "D", "G", "I", "J", "K", "L", "M", "O", "Q"):
            ws.Range(f"{col}{FIRST}:{col}{LAST}").ClearContents()

        # 集金・返金チェックは「名前を入れたら自動で☐/－が出る」数式に戻す
        for r in range(FIRST, LAST + 1):
            ws.Range(f"M{r}").Formula = (
                f'=IF($C{r}="","",IF(OR($D{r}="招待",$D{r}="欠席"),"－","☐"))'
            )
            ws.Range(f"Q{r}").Formula = (
                f'=IF($C{r}="","",IF(OR($P{r}="",$P{r}=0),"－","☐"))'
            )
        # ドロップダウンは維持（数式の上から選択すると値で上書きされる）
        for col, msg in (("M", "集金"), ("Q", "返金")):
            dv = ws.Range(f"{col}{FIRST}:{col}{LAST}").Validation
            try:
                dv.Delete()
            except Exception:
                pass
            dv.Add(Type=xlValidateList, AlertStyle=1, Operator=1, Formula1="☑,☐,－")
            dv.IgnoreBlank = True
            dv.InCellDropdown = True
            dv.ErrorTitle = "入力エラー"
            dv.ErrorMessage = f"☑（{msg}済）・☐（未{msg}）・－（対象外）から選んでください"

        # ── ② 費用の金額を消去（項目名は残す）──
        #    固定費 53-61 / 変動費 3セクション（居酒屋・BBQ・仕入れ対応）
        for r0, r1 in ((53, 61), (68, 71), (76, 80), (85, 89)):
            for col in ("E", "F", "I"):  # 1人当たり予算 / 総額予算 / 実績
                ws.Range(f"{col}{r0}:{col}{r1}").ClearContents()

        # ── ③ イベント情報を消去（種別・会費テーブル・返金設定は残す）──
        #    結合セルは MergeArea 単位でないとクリアできない
        for cell in ("C5", "C6", "C7", "C8", "C9", "C10"):
            rng = wss.Range(cell)
            (rng.MergeArea if rng.MergeCells else rng).ClearContents()

        excel.CalculateFullRebuild()
        wss.Range("C6:E6").NumberFormatLocal = DATE_FMT
        ws.Range("C2:D2").NumberFormatLocal = DATE_FMT

        # ── ④ 検証：個人情報が残っていないか ──
        leftovers = []
        for r in range(FIRST, LAST + 1):
            for col in ("C", "D", "L"):
                v = ws.Range(f"{col}{r}").Value
                if v not in (None, ""):
                    leftovers.append(f"{col}{r}={v}")
        print("残存データ:", leftovers if leftovers else "なし ✅")
        print("参加者数 =", ws.Range("B48").Text[:40])
        print("収入合計 H47 =", ws.Range("H47").Text, "/ 返金合計 P47 =", ws.Range("P47").Text)
        print("会費テーブル 社員 =", wss.Range("C14").Text, "/ 課長 =", wss.Range("C18").Text, "+", wss.Range("D18").Text)

        wb.Save()
        wb.Close(SaveChanges=False)
    finally:
        excel.Quit()
    print("作成:", dst)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2]))
