from pathlib import Path
import json,sys,datetime
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
old_dir=Path(__file__).parent
b=old_dir/'recheck-01';b.mkdir(exist_ok=True)
old=json.loads((old_dir/'project.json').read_text(encoding='utf-8'))
inside=sm.Project(old['internal']);outside=sm.Project(old['external'])
d={'internal':str(inside.path),'external':str(outside.path),'internal_sha256':inside.fingerprint,'external_sha256':outside.fingerprint,'comparison':sm.comparison(inside,outside),'sections':inside.sections,'variable_parts':inside.variable_parts}
(b/'project.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
prev={s['key']:s for s in old['sections']}
changes=[]
for sec in inside.sections:
    p=prev[sec['key']]
    changed=[i for i in range(max(len(p['rows']),len(sec['rows']))) if (p['rows'][i] if i<len(p['rows']) else None)!=(sec['rows'][i] if i<len(sec['rows']) else None)]
    if changed:changes.append({'section':sec['name'],'old_rows':len(p['rows']),'new_rows':len(sec['rows']),'changed_rows':changed})
(b/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'internal_sha':inside.fingerprint,'external_sha':outside.fingerprint,'comparison':d['comparison'],'changes':changes},ensure_ascii=False))
for i,r in enumerate(inside.section('Destacker_段バラシ')['rows']):
    cells=[]
    for c in r['CLs']:
        if c['__type']=='HL':continue
        x={k:c[k] for k in ['__type','Var','Name','Not','X','Y'] if k in c}
        for io in ['In','Out']:
            if c.get(io):x[io]=[(p.get('Arg'),p.get('Var')) for p in c[io] if p.get('Var')]
        cells.append(x)
    print('ROW',i,r.get('CMT','').replace('\r\n',' / '));print(json.dumps({'cells':cells,'VLs':r['VLs']},ensure_ascii=False))
