"""注文書の福西電機ページを読取り専用で確認する。"""
from pathlib import Path
import sys,json
from openpyxl import load_workbook
sys.stdout.reconfigure(encoding='utf-8')
root=Path(r'\\nas-ime5\生産技術部\1.注文書\_内作設備')
files=list((root/'2850-2899'/'2877(AIW-2301改造 AIW-2303T)').rglob('*.xlsx'))
files+=list((root/'2900-2949'/'2910(AIW-2304T) 【AIW-2200DY改造 FP用】').rglob('*.xlsx'))
files+=list((root/'_1.製作中注文書').glob('*FP*/*.xlsx'))
for p in files:
    if p.name.startswith('~$'):continue
    print('\nFILE',str(p),flush=True)
    wb=load_workbook(p,read_only=True,data_only=True,keep_links=False)
    for ws in wb:
        if '福西' not in ws.title and '電気' not in ws.title:continue
        print('TARGET',ws.title,flush=True)
        for r in (4,8,9):
            print('HEADER',r,[str(ws.cell(r,c).value) for c in (2,3,7)],flush=True)
        for rownum,row in enumerate(ws.iter_rows(),1):
            for col in (2,10,18,26,34):
                segment=row[col-1:col+6]
                if any(any(k in str(c.value) for k in ('モータ','モーター','サーボ','MSME','MSMF','MHME')) for c in segment if c.value is not None):
                    print('ITEM',json.dumps([{'cell':c.coordinate,'value':str(c.value)} for c in segment if c.value is not None],ensure_ascii=False),flush=True)
    wb.close()
