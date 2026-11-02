import sys, json, re, collections
from pathlib import Path
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
p=Path(r'C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/資料/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260914A.xlsx')
w=openpyxl.load_workbook(p, data_only=False)
forms={}
for s in w:
    fs={c.coordinate:(c.value if isinstance(c.value,str) else c.value.text) for row in s for c in row if c.data_type=='f'}
    forms[s.title]=fs
    print(s.title,s.max_row,s.max_column,len(fs))
    for a,f in fs.items():
        stripped=re.sub(r'"[^"]*"','',f)
        if re.search(r'(?<![A-Z0-9_])\$?'+re.sub(r'(\d+)',r'\$?\1',a)+r'(?!\d)',stripped):
            print('SELF_CANDIDATE',a,f)
print('CALC',w.calculation)
print('NAMES',list(w.defined_names))
for s in w:
    if 'シリンダ' in s.title:
        for row in s.iter_rows(min_row=49,max_row=60,min_col=12,max_col=29):
            print([(c.coordinate,str(c.value)) for c in row if c.value is not None])
        print('MERGES', [str(m) for m in s.merged_cells if m.min_row<=60 and m.max_row>=49])
        c=s['T56']; print('ARRAY',vars(c.value))
import zipfile, xml.etree.ElementTree as ET
with zipfile.ZipFile(p) as z:
    data=z.read('xl/worksheets/sheet3.xml').decode()
    print('T56XML',re.search(r'<c\b[^>]*r="T56".*?</c>',data).group(0))
    print('PACKAGE',z.namelist())
Path(__file__).with_name('formulas.json').write_text(json.dumps(forms,ensure_ascii=False,indent=2),encoding='utf-8')
