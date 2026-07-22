# Excel COM で再計算して保存（Windows用recalc）
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import win32com.client

path = os.path.abspath(sys.argv[1])
excel = win32com.client.DispatchEx("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False
try:
    wb = excel.Workbooks.Open(path)
    excel.CalculateFullRebuild()
    wb.Save()
    wb.Close(SaveChanges=False)
    print("再計算・保存完了:", path)
finally:
    excel.Quit()
