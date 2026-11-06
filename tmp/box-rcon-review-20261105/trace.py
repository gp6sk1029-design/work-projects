from pathlib import Path
from collections import defaultdict
import json,re
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
w=defaultdict(list);reads=defaultdict(list)
for s in d['sections']:
 for i,r in enumerate(s['rows']):
  for c in r['CLs']:
   v=c.get('Var','')
   if re.fullmatch(r'RCON2_\d+_Auto\[\d+\]',v):
    (w if c['__type']=='ST' else reads if c['__type']=='LD' else defaultdict(list))[v].append((s['name'],i))
print('MAP',json.dumps({v:{'coils':rs,'contacts':reads[v]} for v,rs in w.items()},ensure_ascii=False))
for s in d['sections']:
 if s['name']!='RCON_IAI':continue
 for i,r in enumerate(s['rows']):
  if any(re.search(r'RCON2_[2345]_(Auto\[|MoveDone)',c.get('Var','')) for c in r['CLs']):print('RECEIVE',i,json.dumps(r,ensure_ascii=False))
(b/'request_map.json').write_text(json.dumps({v:{'coils':rs,'contacts':reads[v]} for v,rs in w.items()},ensure_ascii=False,indent=2),encoding='utf-8')
