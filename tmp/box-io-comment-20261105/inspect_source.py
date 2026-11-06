from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,re,hashlib
b=Path(__file__).parent
prior=json.loads((b.parent/'box-comment-layout-20261105/verification.json').read_text(encoding='utf-8'))
p=Path(prior['output']);raw=p.read_bytes();data={'source':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'sections':[],'scopes':[]}
with ZipFile(p) as z:
    for n in z.namelist():
        if n.endswith('.oem'):
            for e in E.fromstring(z.read(n)).iter():
                if e.get('type')!='PouBody':continue
                part=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml';t=z.read(part).decode('utf-8-sig')
                if t.lstrip().startswith('{"CLs"'):data['sections'].append({'name':e.get('name'),'part':part,'rows':[json.loads(l) for l in t.splitlines()]})
        if n.endswith('.xml'):
            t=z.read(n).decode('utf-8-sig',errors='replace')
            if t.startswith('[SLWD') and 'N=BoxPacking_M\t' in t:data['scopes'].append({'part':n,'text':t})
(b/'project.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
(b/'source.smc2').write_bytes(raw)
print('SHA',data['sha256'])
for s in data['sections']:
    if s['name'] not in ['BoxPacking_箱詰め','ST7_A_Dis2_左SF排出','RCON_IAI']:continue
    for i,r in enumerate(s['rows']):
        hits=[l for l in r.get('CMT','').splitlines() if re.search(r'[XY]\d+',l)]
        if hits:print(s['name'],i,json.dumps(hits,ensure_ascii=False))
