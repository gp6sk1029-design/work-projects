"""最新F版を読取り専用で取得し、対象セクションと変数スコープを照合する。"""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import hashlib,json,re

b=Path(__file__).parent
src=Path('C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/0.DLデータ/OMRON/Codex編集用/3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105F.smc2')
raw=src.read_bytes()
data={'source':str(src),'sha256':hashlib.sha256(raw).hexdigest(),'sections':[],'scopes':[],'oem':[]}
with ZipFile(src) as z:
    for n in z.namelist():
        if n.endswith('.oem'):
            root=E.fromstring(z.read(n)); data['oem'].append({'part':n,'text':z.read(n).decode('utf-8-sig')})
            for e in root.iter():
                if e.get('type')=='PouBody':
                    part=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'
                    t=z.read(part).decode('utf-8-sig')
                    if t.lstrip().startswith('{"CLs"'):
                        data['sections'].append({'name':e.get('name'),'part':part,'rows':[json.loads(l) for l in t.splitlines()]})
        if n.endswith('.xml'):
            t=z.read(n).decode('utf-8-sig',errors='replace')
            if t.startswith('[SLWD'):
                data['scopes'].append({'part':n,'text':t})
(b/'project.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
(b/'source.smc2').write_bytes(raw)
print('source_sha256',data['sha256'],'bytes',len(raw))
print('sections',[(s['name'],len(s['rows'])) for s in data['sections']])
for s in data['scopes']:
    lines=s['text'].splitlines()
    relevant=[l for l in lines if any('N='+n+'\t' in l for n in ['BoxPacking_M','BoxPacking_A_Busy','ST7_A_SF_Wait_Pickup','Box_Total_CT','ST7_A_SF_M'])]
    if relevant:
        print('SCOPE',s['part'],lines[:8]); print('\n'.join(relevant))
for s in data['sections']:
    if s['name']=='BoxPacking_箱詰め':
        print('FIRST',json.dumps(s['rows'][:2],ensure_ascii=False))
        print('PICKUP',json.dumps({i:s['rows'][i] for i in [27,28,35,36,41]},ensure_ascii=False))
