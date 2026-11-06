from pathlib import Path
import json,sys
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
root=Path(__file__).parent;b=root/'recheck-02';b.mkdir(exist_ok=True)
old=json.loads((root/'recheck-01/project.json').read_text(encoding='utf-8'))
p=sm.Project(old['internal']);ext=sm.Project(old['external'])
d={'internal':str(p.path),'external':str(ext.path),'internal_sha256':p.fingerprint,'external_sha256':ext.fingerprint,'sections':p.sections,'variable_parts':p.variable_parts,'comparison':sm.comparison(p,ext)}
(b/'project.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
before={s['key']:s for s in old['sections']};changes=[]
for sec in p.sections:
    previous=before.get(sec['key'],{'rows':[]})['rows'];rows=sec['rows']
    ix=[i for i in range(max(len(previous),len(rows))) if (previous[i] if i<len(previous) else None)!=(rows[i] if i<len(rows) else None)]
    if ix:changes.append({'section':sec['name'],'previous_rows':len(previous),'current_rows':len(rows),'changed_rows':ix})
(b/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'sha':p.fingerprint,'changes':changes,'external_comparison':d['comparison']},ensure_ascii=False))
for i,r in enumerate(p.section('Destacker_段バラシ')['rows']):
    cells=[]
    for c in r['CLs']:
        if c['__type']=='HL':continue
        x={k:c[k] for k in ['__type','Var','Name','Not','X','Y','Id'] if k in c}
        for io in ['In','Out']:
            if c.get(io):x[io]=[(z.get('Arg'),z.get('Var')) for z in c[io] if z.get('Var')]
        cells.append(x)
    print('ROW',i,r.get('CMT','').replace('\r\n',' / '));print(json.dumps({'cells':cells,'VLs':r['VLs']},ensure_ascii=False))
