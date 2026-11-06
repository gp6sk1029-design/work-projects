"""対象シート、E列の入力値、G列の既存例を保存せずに確認する。"""
from pathlib import Path
import json
import hashlib
import openpyxl

base=Path(__file__).parent
p=Path(r'C:\Users\SEIGI-N13\Desktop\1029_1332エンコーダ基準.xlsx')
wb=openpyxl.load_workbook(p,data_only=False)
cached=openpyxl.load_workbook(p,data_only=True)
out={'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sheets':[]}
for ws in wb:
    rows=[]
    for row in ws:
        for c in row:
            if c.column==5 and c.value is not None:
                rows.append({'row':c.row,'value':c.value,'cached':cached[ws.title][c.coordinate].value,'D':ws.cell(c.row,4).value})
    out['sheets'].append({'name':ws.title,'max_row':ws.max_row,'max_column':ws.max_column,'E_count':len(rows),'E_first':rows[:5],'E_last':rows[-4:],'G_first':[{'cell':f'G{r}','value':ws[f'G{r}'].value,'style':ws[f'G{r}'].style_id,'format':ws[f'G{r}'].number_format} for r in range(4,10)],'G_nonempty':sum(ws.cell(r,7).value is not None for r in range(5,365)),'F_sequence':[ws.cell(r,6).value for r in range(5,365)] if ws.title=='Sheet1' else [],'E_all':rows})
(base/'inspection.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps({'sha256':out['sha256'],'target':[{k:v for k,v in s.items() if k not in ('E_all','F_sequence')} for s in out['sheets'] if s['name']=='Sheet1']},ensure_ascii=False,default=str))
