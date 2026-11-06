"""最新B版の箱詰めセクションと段番号の参照を確認する。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,re,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104B.smc2')
def vars(x,path):
 if isinstance(x,dict):
  if isinstance(x.get('Var'),str) and re.fullmatch(r'BoxPacking_M\[\d+\]',x['Var']):yield {'path':path,**{k:v for k,v in x.items() if k in ['__type','Ix','Var','X','Y','Not']}}
  for k,v in x.items():yield from vars(v,path+[k])
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from vars(v,path+[i])
with zipfile.ZipFile(src) as z:
 assert z.testzip() is None
 sections=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody' and e.get('name')=='BoxPacking_箱詰め':sections.append(n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml')
 assert len(sections)==1;part=sections[0]
 rows=[json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines()]
 refs=list(vars(rows,[]));coils=[e for e in refs if e['__type']=='ST']
 view=[{'row':i,'comment':r.get('CMT',''),'coils':[e['Var'] for e in coils if e['path'][0]==i],'references':[e for e in refs if e['path'][0]==i]} for i,r in enumerate(rows)]
 outside=[]
 for n in z.namelist():
  if n==part:continue
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  hits=re.findall(r'BoxPacking_M\[(\d+)\]',t)
  if hits:outside.append({'part':n,'indices':sorted(set(map(int,hits)))})
 data={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'parts':len(z.namelist()),'target':part,'row_count':len(rows),'coils':[e['Var'] for e in coils],'view':view,'outside_references':outside}
 (b/'inspection.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 (b/'rows_before.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(data,ensure_ascii=False))
