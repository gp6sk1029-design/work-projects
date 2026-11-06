"""更新されたC版の後半工程と参照を確認する。"""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from collections import Counter
import hashlib,json,re
b=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\Codex編集用\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105D.smc2')
result={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'references':[],'declarations':[]}
with ZipFile(src) as z:
 assert z.testzip() is None
 sections=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'})
 target=[s for s in sections if s['name']=='BoxPacking_箱詰め'];assert len(target)==1;result['target']=target[0]
 coils=[]
 for s in sections:
  t=z.read(s['part']).decode('utf-8-sig');rr=re.findall(r'BoxPacking_M\[(\d+)\]',t)
  if rr:result['references'].append({'section':s['name'],'part':s['part'],'count':len(rr)})
  if s!=target[0]:continue
  rows=[json.loads(l) for l in t.splitlines()];result['row_count']=len(rows)
  for i,r in enumerate(rows):
   c=[e['Var'] for e in r['CLs'] if e['__type']=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',e.get('Var',''))];coils+=c
   if 0<=i<=60:print('ROW',i,json.dumps(r,ensure_ascii=False))
  result['coils']=coils;result['duplicates']={k:v for k,v in Counter(coils).items() if v>1}
 for n in z.namelist():
  t=z.read(n).decode('utf-8-sig',errors='replace')
  if t.startswith('[SLWD'):
   for line in t.splitlines():
    if '\tN=BoxPacking_M\t' in line:result['declarations'].append({'part':n,'line':line})
 (b/'inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY',json.dumps(result,ensure_ascii=False))
