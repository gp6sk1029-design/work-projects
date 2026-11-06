from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,re,hashlib
b=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\Codex編集用\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105D.smc2')
data={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'sections':[]}
with ZipFile(src) as z:
 sections=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'})
 for s in sections:
  text=z.read(s['part']).decode('utf-8-sig')
  if not text.lstrip().startswith('{"CLs"'):continue
  s['rows']=[json.loads(l) for l in text.splitlines()];data['sections'].append(s)
 (b/'project.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
 for s in data['sections']:
  if s['name']=='BoxPacking_箱詰め':
   for i,r in enumerate(s['rows']):
    print(i, json.dumps({'contacts':[(c.get('Var'),c.get('Not',False)) for c in r['CLs'] if c['__type']=='LD'],'coils':[c.get('Var') for c in r['CLs'] if c['__type']=='ST'],'functions':[(c.get('Name'),[(p.get('Arg'),p.get('Var')) for p in c.get('In',[])+c.get('Out',[]) if p.get('Var')]) for c in r['CLs'] if c['__type']=='F']},ensure_ascii=False))
 print('SHA',data['sha256'])
 for s in data['sections']:
  if 'RCON' in s['name']:print('RCON_SECTION',s['name'],len(s['rows']))
