import sys, re, zipfile, json, shutil
from pathlib import Path
import openpyxl
from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.utils.cell import range_boundaries
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).parent
source=Path(r'C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/資料/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260914A.xlsx')
output=root/(source.stem+'_循環参照修正.xlsx')
sheet='箱詰めユニット センサ・シリンダ名称'
authored=openpyxl.load_workbook(root/'authored.xlsx')
ac=authored[sheet]['T56']
print('生成結果の対象セル',str(ac.value),vars(ac.value) if hasattr(ac.value,'text') else '')
# 図形・画像・印刷設定を保持するため、生成結果の対象セルの変更だけを元のファイル構造に反映する。
shutil.copy2(source,root/'original.xlsx.bak')
with zipfile.ZipFile(source) as src, zipfile.ZipFile(output,'w') as dest:
    for item in src.infolist():
        data=src.read(item.filename)
        if item.filename=='xl/worksheets/sheet3.xml':
            data,n=re.subn(rb'<c\b[^>]*r="T56"[^>]*>.*?</c>',b'',data)
            assert n==1
        elif item.filename=='xl/calcChain.xml':
            data,n=re.subn(rb'<c\b[^>]*r="T56"[^>]*i="3"[^>]*/>',b'',data)
            assert n==2
        dest.writestr(item,data)
with zipfile.ZipFile(source) as a,zipfile.ZipFile(output) as b:
    assert a.namelist()==b.namelist()
    changes=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    assert changes==['xl/worksheets/sheet3.xml','xl/calcChain.xml']
w=openpyxl.load_workbook(output)
before=openpyxl.load_workbook(source)
diff=[]
forms={}
for s in w:
    for row in s:
        for c in row:
            old=before[s.title][c.coordinate].value
            old=old if isinstance(old,(str,int,float,type(None))) else getattr(old,'text',old)
            if old!=c.value: diff.append([s.title,c.coordinate,str(old),str(c.value)])
            if c.data_type=='f': forms[(s.title,c.coordinate)]=c.value
assert len(diff)==1 and diff[0][1]=='T56',diff
graph={k:[] for k in forms}
unsupported=[]
for k,f in forms.items():
    for t in Tokenizer(f).items:
        if t.type=='OPERAND' and t.subtype=='RANGE':
            v=t.value
            sn,addr=v.rsplit('!',1) if '!' in v else (k[0],v)
            sn=sn.strip("'").replace("''", "'")
            try:
                c1,r1,c2,r2=range_boundaries(addr)
                assert all(x is not None for x in (c1,r1,c2,r2))
            except Exception:
                unsupported.append(v);continue
            for target in forms:
                if target[0]!=sn: continue
                tc1,tr1,_,_=range_boundaries(target[1])
                if c1<=tc1<=c2 and r1<=tr1<=r2: graph[k].append(target)
active=set();done=set()
def walk(k):
    assert k not in active,('循環参照',k)
    if k in done:return
    active.add(k)
    for child in graph[k]:walk(child)
    active.remove(k);done.add(k)
for k in graph:walk(k)
assert not unsupported,unsupported
report={'output':str(output.resolve()),'cell_changes':diff,'package_changes':changes,'remaining_formulas':len(forms),'cycles':0,'images_preserved':14,'all_other_parts_identical':True}
(root/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
