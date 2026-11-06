"""当日原本の段バラシ行と添字を読み取り専用で確認する。"""
from pathlib import Path
import zipfile,json,re,hashlib,sys
from lxml import etree as E
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261103A.smc2')
def variables(x):
 if isinstance(x,dict):
  if 'Var' in x:yield {k:v for k,v in x.items() if k in ['__type','Ix','X','Y','Var']}
  for v in x.values():yield from variables(v)
 elif isinstance(x,list):
  for v in x:yield from variables(v)
with zipfile.ZipFile(src) as z:
 assert z.testzip() is None
 oems=[n for n in z.namelist() if n.endswith('.oem')]
 found=[]
 for name in oems:
  r=E.fromstring(z.read(name))
  for el in r.iter():
   if el.get('name')=='Destacker_段バラシ':found.append((name,el.attrib))
 assert len(found)==1,found
 folder=found[0][0].rsplit('/',1)[0]
 part=folder+'/'+found[0][1]['id']+'.xml'
 rows=[json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines() if l.strip()]
 view=[]
 for i,row in enumerate(rows):
  vs=list(variables(row))
  view.append({'行':i,'コイル':[v['Var'] for v in vs if v.get('__type')=='ST' and v['Var'].startswith('Destacker_M[')],'参照':[v for v in vs if v['Var'].startswith('Destacker_M[')]})
 others=[]
 for n in z.namelist():
  if n==part:continue
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  refs=re.findall(r'Destacker_M\s*\[\d+\]',t)
  if refs:others.append({'part':n,'refs':sorted(set(refs))})
 data={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'target':part,'row_count':len(rows),'view':view,'outside_references':others}
 (base/'inspection.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(data,ensure_ascii=False))
