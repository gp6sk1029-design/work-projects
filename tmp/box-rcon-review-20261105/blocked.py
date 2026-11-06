from pathlib import Path
import json,re
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
out=[]
for s in d['sections']:
 for i,r in enumerate(s['rows']):
  for c in r['CLs']:
   if c['__type']=='F' and c.get('Name')=='MOVE':
    pp=[p.get('Var','') for p in c.get('In',[])+c.get('Out',[]) if p.get('__type')=='PRM']
    if any(re.search(r'RCON2_(?:OUT\[[2345]\]\.TargetPos_mm|[2345]_IN_(?:ControllerReady|ServoReady|PositionDone))',p) for p in pp):
     out.append({'section':s['name'],'row':i,'contacts':[x.get('Var') for x in r['CLs'] if x['__type']=='LD'],'values':pp})
   if c['__type']=='ST' and re.fullmatch(r'RCON2_OUT\[[2345]\]\.Control.Start',c.get('Var','')):out.append({'section':s['name'],'row':i,'contacts':[x.get('Var') for x in r['CLs'] if x['__type']=='LD'],'coil':c['Var']})
(b/'blocked_paths.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for r in out:print(json.dumps(r,ensure_ascii=False))
