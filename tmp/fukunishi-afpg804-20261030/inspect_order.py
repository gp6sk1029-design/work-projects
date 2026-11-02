"""福西電機経費ブックと採番規則を読み取り確認する。"""
from pathlib import Path
import openpyxl,sys,json,hashlib
sys.stdout.reconfigure(encoding='utf-8')
B=Path(__file__).resolve().parent
S=Path(r'\\nas-ime5\生産技術部\1.注文書\A【経費】 10万円以下 修理部品 消耗部品 等\A【注文書】F 福西電機 2026.xlsx')
print('LOCK',S.with_name('~$'+S.name).exists())
w=openpyxl.load_workbook(S,data_only=False)
print('SHEETS',w.sheetnames)
for s in w:
 print('SHEET',s.title,'DATE',str(s['G4'].value),'ORDER',s['C8'].value,'BILL',s['C9'].value,'DELIVER',s['C10'].value)
 print('DETAIL',[(s.cell(i,2).value,s.cell(i,3).value,s.cell(i,5).value,s.cell(i,6).value) for i in range(17,41) if s.cell(i,2).value])
 if s.title=='原紙':
  print('TEMPLATE',[(c.coordinate,str(c.value)) for row in s.iter_rows(min_row=1,max_row=44,min_col=2,max_col=8) for c in row if c.value is not None])
  print('PRINT',str(s.print_area),s.page_setup.orientation,s.page_setup.paperSize)
w.close()
R=Path(r'\\nas-ime5\生産技術部\1.注文書\__注文番号ルール 20260401ー.xlsx')
rw=openpyxl.load_workbook(R,data_only=False)
for s in rw:
 print('RULE_SHEET',s.title)
 for row in s:
  if any(c.value and any(x in str(c.value) for x in ('福西','経費','幸田','AU-','AF-')) for c in row):
   print('RULE',[(c.coordinate,str(c.value)) for c in row if c.value is not None])
rw.close()
(B/'inspection.json').write_text(json.dumps({'source':str(S),'sha256':hashlib.sha256(S.read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
