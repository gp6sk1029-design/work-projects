import sys,json,hashlib,shutil,re
from pathlib import Path
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
d=Path(__file__).parent
folder=Path(r'\\nas-ime5\生産技術部\1.注文書\_内作設備\_1.製作中注文書\2717-2610A インナー巻線機 (AIW-1100T) 〈2台〉【マーレOH】')
assert not list(folder.glob('~$*')),'Excelが開かれています'
p=next(folder.glob('*.xlsx'))
if not (d/'before.xlsx').exists():shutil.copy2(p,d/'before.xlsx')
assert hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256((d/'before.xlsx').read_bytes()).hexdigest()
w=openpyxl.load_workbook(d/'before.xlsx',read_only=False,data_only=False)
targets={}
for s in w:
 cells=set()
 for row in s.iter_rows():
  for c in row:
   v=c.value
   if not isinstance(v,str):continue
   clean=re.sub(r'[\s　]','',v).replace('$','').replace("'",'')
   if c.data_type=='f' and '集計表!C4' in clean:cells.add(c.coordinate)
   if s.title not in ('集計表','発注先') and c.data_type!='f' and clean.rstrip('：:')=='設備名':
    right=s.cell(c.row,c.column+1)
    if right.value is not None:cells.add(right.coordinate)
 if s.title=='集計表':cells.update(['C4','K4','U4'])
 if cells:
  targets[s.title]=sorted(cells,key=lambda a:(s[a].row,s[a].column))
  print(s.title,[(a,s[a].alignment.shrinkToFit,s[a].alignment.wrapText) for a in targets[s.title]])
m={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'targets':targets}
(d/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print('対象数',sum(map(len,targets.values())))
w.close()
