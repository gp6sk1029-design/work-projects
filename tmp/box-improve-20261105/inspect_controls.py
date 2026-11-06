from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,re,hashlib
b=Path(__file__).parent
old=json.loads((b.parent/'box-rcon-review-20261105/project.json').read_text(encoding='utf-8'))
src=Path(old['source']);data={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'sections':[],'variables':[]}
with ZipFile(src) as z:
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')!='PouBody':continue
    part=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml';t=z.read(part).decode('utf-8-sig')
    if t.lstrip().startswith('{"CLs"'):data['sections'].append({'name':e.get('name'),'part':part,'rows':[json.loads(l) for l in t.splitlines()]})
 for n in z.namelist():
  t=z.read(n).decode('utf-8-sig',errors='replace')
  if t.startswith('[SLWD'):
   for line in t.splitlines():
    if re.search(r'\bN=(?:RCON2_(?:MotionPermit|CommOK|WriteEnable|AxisApply|LayoutConfirmed|ByteOrderConfirmed)|RCON2_[2345]_|Box_Total_CT)',line):data['variables'].append({'part':n,'line':line})
 (b/'project.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
 print('SHA',data['sha256'])
 for s in data['sections']:
  if s['name']=='RCON_IAI':
   for i in list(range(203,210))+list(range(283,323)):
    r=s['rows'][i]
    print(i,json.dumps({'contacts':[(c.get('Var'),c.get('Not',False)) for c in r['CLs'] if c['__type']=='LD'],'coils':[c.get('Var') for c in r['CLs'] if c['__type']=='ST'],'functions':[(c.get('Name'),[(p.get('Arg'),p.get('Var')) for p in c.get('In',[])+c.get('Out',[]) if p.get('Var')]) for c in r['CLs'] if c['__type']=='F']},ensure_ascii=False))
 for s in data['sections']:
  for i,r in enumerate(s['rows']):
   if any('RCON2_MotionPermit' in c.get('Var','') for c in r['CLs']):print('PERMIT',s['name'],i,json.dumps(r,ensure_ascii=False)[:1000])
