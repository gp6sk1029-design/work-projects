"""NTS経費注文書を読取り、日付タブ・採番・原紙・ロックを確認する。標準inspectを隠さない。"""
from pathlib import Path
import hashlib,json,sys,zipfile
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SRC=Path(r'\\nas-ime5\生産技術部\1.注文書\A【経費】 10万円以下 修理部品 消耗部品 等\A【注文書】B NTS2026.xlsx')
print('LOCK',SRC.with_name('~$'+SRC.name).exists())
w=openpyxl.load_workbook(SRC,data_only=False)
print('SHEETS',w.sheetnames)
for s in w:
    print('ORDER',s.title,'DATE',str(s['G4'].value),'NO',s['C8'].value,'ITEM',s['B17'].value)
s=w['原紙']
for row in s.iter_rows(min_row=1,max_row=44,min_col=2,max_col=8):
    vals={c.coordinate:str(c.value) for c in row if c.value is not None}
    if vals:print('TEMPLATE',vals)
print('PRINT',s.page_setup,s.print_area,'ZERO',s.sheet_view.showZeros)
with zipfile.ZipFile(SRC) as z:
    xmls={n:z.read(n).decode('utf-8') for n in ['xl/workbook.xml','xl/_rels/workbook.xml.rels','[Content_Types].xml']}
(BASE/'inspection.json').write_text(json.dumps({'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'sheets':w.sheetnames,'xmls':xmls},ensure_ascii=False),encoding='utf-8')
w.close()
