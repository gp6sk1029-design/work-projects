# Excel COMで開催日を日付書式に（NumberFormatLocalで日本語ロケール指定）。再計算→書式設定→保存の順
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import win32com.client

path = os.path.abspath(sys.argv[1])
DATE_FMT = 'yyyy"年"m"月"d"日"'
excel = win32com.client.DispatchEx("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False
try:
    wb = excel.Workbooks.Open(path)
    ws_set = wb.Worksheets("設定")
    ws_mgmt = wb.Worksheets("収支管理")
    excel.CalculateFullRebuild()
    # 書式は計算の後・保存の直前に設定（正規化を避ける）。NumberFormatLocalで日本語書式
    ws_set.Range("C6:E6").NumberFormatLocal = DATE_FMT
    ws_mgmt.Range("C2:D2").NumberFormatLocal = DATE_FMT
    wb.Save()
    print("設定C6 表示=", ws_set.Range("C6").Text, "| 書式=", ws_set.Range("C6").NumberFormatLocal)
    print("収支C2 表示=", ws_mgmt.Range("C2").Text, "| 書式=", ws_mgmt.Range("C2").NumberFormatLocal)
    wb.Close(SaveChanges=False)
finally:
    excel.Quit()
