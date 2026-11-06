"""最新A版の箱詰め番号順と他セクションの参照を調べる。"""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import hashlib,json,re

b=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105A.smc2')
raw=src.read_bytes();result={'source':str(src),'sha256':hashlib.sha256(raw).hexdigest(),'sections':[],'references':[],'declarations':[]}
with ZipFile(src) as z:
 assert z.testzip() is None
 sections=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'})
 targets=[s for s in sections if s['name']=='BoxPacking_箱詰め'];assert len(targets)==1
 result['target']=targets[0]
 for s in sections:
  t=z.read(s['part']).decode('utf-8-sig')
  if not t.lstrip().startswith('{'):continue
  rows=[json.loads(l) for l in t.splitlines() if l.strip()]
  if s==targets[0]:
   result['row_count']=len(rows)
   for i,r in enumerate(rows):
    coils=[e.get('Var') for e in r['CLs'] if e['__type']=='ST' and e.get('Var','').startswith('BoxPacking_M[')]
    refs=re.findall(r'BoxPacking_M\[\d+\]',json.dumps(r))
    print(json.dumps({'row':i,'coils':coils,'refs':refs,'comment':r.get('CMT','')[:100]},ensure_ascii=False))
  if 'BoxPacking_M' in t:
   info={'section':s['name'],'part':s['part'],'indices':sorted(set(map(int,re.findall(r'BoxPacking_M\[(\d+)\]',t)))),'reference_count':len(re.findall(r'BoxPacking_M\[(\d+)\]',t))}
   result['references'].append(info)
 for n in z.namelist():
  t=z.read(n).decode('utf-8-sig',errors='replace')
  if t.startswith('[SLWD'):
   for line in t.splitlines():
    if '\tN=BoxPacking_M\t' in line:result['declarations'].append({'part':n,'line':line})
 (b/'inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY',json.dumps(result,ensure_ascii=False))
