"""FPH注文書の部品移動・発注の区別を確認する。"""
from pathlib import Path
import sys,json,hashlib
from openpyxl import load_workbook
sys.stdout.reconfigure(encoding='utf-8')
root=Path(r'\\nas-ime5\生産技術部\1.注文書\_内作設備\2850-2899\2877(AIW-2301改造 AIW-2303T)')
p=next(root.rglob('*FPH*注文書.xlsx'))
print('FILE',p)
print('SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
w=load_workbook(p,read_only=True,data_only=True,keep_links=False)
s=w['福西']
for bounds in ((2,8),(10,16)):
    print('BLOCK',bounds)
    for row in s.iter_rows(min_row=1,max_row=44,min_col=bounds[0],max_col=bounds[1]):
        cells=[(c.coordinate,str(c.value)) for c in row if c.value is not None]
        if cells:print(json.dumps(cells,ensure_ascii=False))
w.close()
