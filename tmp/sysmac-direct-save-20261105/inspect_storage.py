"""Sysmac内部Hと外部Hを読取り比較。内部ファイルは変更しない。"""
from pathlib import Path
from lxml import etree as E
from zipfile import ZipFile
import json,hashlib
b=Path(__file__).parent
base=Path('C:/OMRON/Data/Solution/fe78558c-1d0e-41d5-9b83-730179a87edb')
root_oem=base/(base.name+'.oem')
prev=json.loads((b.parent/'box-io-comment-20261105/verification.json').read_text(encoding='utf-8'))
external=Path(prev['output'])
report={'internal_directory':str(base),'external_file':str(external),'oem_files':[],'internal_sections':[],'external_sections':[],'comparisons':[]}
for p in base.rglob('*.oem'):
    rt=E.fromstring(p.read_bytes())
    names=[{'type':e.get('type'),'name':e.get('name'),'id':e.get('id')} for e in rt.iter() if e.tag=='Entity' and e.get('type') in ['Solution','NexDevice']]
    report['oem_files'].append({'path':str(p),'entities':names})
    for e in rt.iter():
        if e.get('type')!='PouBody':continue
        candidates=list(base.rglob(e.get('id')+'.xml'))
        if len(candidates)!=1:continue
        f=candidates[0];t=f.read_bytes().decode('utf-8-sig')
        if t.lstrip().startswith('{"CLs"'):
            rows=[json.loads(l) for l in t.splitlines()]
            report['internal_sections'].append({'name':e.get('name'),'path':str(f),'rows':rows,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
with ZipFile(external) as z:
    for n in z.namelist():
        if not n.endswith('.oem'):continue
        for e in E.fromstring(z.read(n)).iter():
            if e.get('type')!='PouBody':continue
            part=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml';t=z.read(part).decode('utf-8-sig')
            if t.lstrip().startswith('{"CLs"'):
                report['external_sections'].append({'name':e.get('name'),'part':part,'rows':[json.loads(l) for l in t.splitlines()]})
inside={s['name']:s for s in report['internal_sections']}
for s in report['external_sections']:
    if s['name'] not in inside:continue
    other=inside[s['name']]
    cr={'name':s['name'],'same':s['rows']==other['rows'],'internal_rows':len(other['rows']),'external_rows':len(s['rows'])}
    if len(s['rows'])==len(other['rows']):
        cr['comment_difference_rows']=[i for i,(a,c) in enumerate(zip(s['rows'],other['rows'])) if a.get('CMT')!=c.get('CMT')]
        cr['logic_difference_rows']=[i for i,(a,c) in enumerate(zip(s['rows'],other['rows'])) if {k:v for k,v in a.items() if k!='CMT'}!={k:v for k,v in c.items() if k!='CMT'}]
    report['comparisons'].append(cr)
(b/'inspection.json').write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'internal_directory':str(base),'oems':report['oem_files'],'section_count':len(inside),'differences':[c for c in report['comparisons'] if not c['same']]},ensure_ascii=False,indent=2))
for suffix in ['.manifest','.manifest2','.xml','.SolutionUserData','.PersistenceUserData']:
    p=base/(base.name+suffix)
    if p.exists():
        print('METADATA',p.name,p.stat().st_size)
        if suffix in ['.manifest','.xml']:print(p.read_text(encoding='utf-8-sig')[:1300])
