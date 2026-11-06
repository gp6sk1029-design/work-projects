"""保存済みHの段バラシと受け側を読取り調査する。"""
from pathlib import Path
import sys,json,re,time
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent
meta=json.loads((b.parent/'box-io-comment-20261105/verification.json').read_text(encoding='utf-8'))
inside=sm.Project('C:/OMRON/Data/Solution/fe78558c-1d0e-41d5-9b83-730179a87edb');outside=sm.Project(meta['output'])
comparison=sm.comparison(inside,outside)
data={'internal':str(inside.path),'external':str(outside.path),'internal_sha256':inside.fingerprint,'external_sha256':outside.fingerprint,'comparison':comparison,
      'sections':inside.sections,'variable_parts':inside.variable_parts}
(b/'project.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
print('COMPARISON',json.dumps(comparison,ensure_ascii=False))
dest=inside.section('Destacker_段バラシ')
for i,r in enumerate(dest['rows']):
    cs=[]
    for c in r['CLs']:
        if c['__type']=='HL':continue
        cs.append({k:c[k] for k in ['__type','Var','Name','Not','X','Y','TXT'] if k in c}|{
            'In':[(p.get('Arg'),p.get('Var')) for p in c.get('In',[]) if p.get('Var')],
            'Out':[(p.get('Arg'),p.get('Var')) for p in c.get('Out',[]) if p.get('Var')]})
    print('ROW',i,r.get('CMT','').replace('\r\n',' / '));print(json.dumps({'cells':cs,'VLs':r['VLs']},ensure_ascii=False))
tags=set(c['Var'].split('[')[0] for r in dest['rows'] for c in r['CLs'] if c['__type']=='ST')
refs=[]
for s in inside.sections:
    for i,r in enumerate(s['rows']):
        if s['name']=='Destacker_段バラシ':continue
        if any(any(c.get('Var','').startswith(t+'[') or c.get('Var','')==t for t in tags) for c in r['CLs']):
            refs.append({'section':s['name'],'row':i,'CMT':r.get('CMT',''),'rung':r})
(b/'cross_references.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding='utf-8')
print('OTHER_REFERENCES',[(r['section'],r['row']) for r in refs])
