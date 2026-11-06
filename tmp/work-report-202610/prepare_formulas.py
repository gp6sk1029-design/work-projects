"""元の式を読取り、計算確認用コピーだけで互換形へ展開する。"""
from pathlib import Path
import sys
sys.path=[p for p in sys.path if Path(p or '.').resolve()!=Path(__file__).parent.resolve()]
import json
import re
import openpyxl

base=Path(__file__).parent
src=base/'backup'/'【業務報告2026 Ver2.7】幸田_編集前.xlsx'
wb=openpyxl.load_workbook(src,data_only=False)
values=openpyxl.load_workbook(src,data_only=True)
maps={}
for title in ('年間集計','10月'):
    out=[]
    for row in wb[title]:
        for c in row:
            f=c.value
            if hasattr(f,'text'):f=f.text
            if not isinstance(f,str) or not f.startswith('='):continue
            original=f
            m=re.fullmatch(r'=INDIRECT\(([A-Z]+\$?\d+)&"!([A-Z]+\d+)"\)',f)
            if m:
                tab=values[title][m[1].replace('$','')].value
                f=f"='{tab}'!{m[2]}"
            m=re.fullmatch(r'=SUM\(IFERROR\(([A-Z]+\d+:[A-Z]+\d+),0\)\)',f)
            if m:f=f'=SUM({m[1]})'
            out.append({'cell':c.coordinate,'formula':f,'original':original})
    maps[title]=out
(base/'formula_map.json').write_text(json.dumps(maps,ensure_ascii=False,indent=2),encoding='utf-8')
print({title:len(v) for title,v in maps.items()})
