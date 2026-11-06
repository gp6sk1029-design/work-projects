from pathlib import Path
from zipfile import ZipFile
from collections import defaultdict
import json,re,hashlib
b=Path(__file__).parent;m=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
with ZipFile(m['source']) as z:
 rows=[json.loads(l) for l in z.read(m['target']['part']).decode('utf-8-sig').splitlines()]
 requests=sorted({c['Var'] for r in rows for c in r['CLs'] if c['__type']=='ST' and ('_Auto[' in c.get('Var',''))})
 consumers=defaultdict(list);writers=defaultdict(list)
 for n in z.namelist():
  text=z.read(n).decode('utf-8-sig',errors='replace')
  if not text.lstrip().startswith('{"CLs"'):continue
  for i,line in enumerate(text.splitlines()):
   r=json.loads(line)
   for c in r['CLs']:
    if c.get('Var') in requests and c['__type']=='LD':consumers[c['Var']].append([n,i])
    if c['__type']=='F':
     for p in c.get('Out',[]):
      if p.get('Var')=='Box_Total_CT':writers['Box_Total_CT'].append([n,i,c['Name']])
 inventory={'request_contacts':{v:consumers[v] for v in requests},'counter_writers':writers,'source_sha256':m['sha256']}
 (b/'cross_reference.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'requests_without_contacts':[v for v in requests if not consumers[v]],'counter_writers':writers},ensure_ascii=False))
 assert hashlib.sha256(Path(m['source']).read_bytes()).hexdigest()==m['sha256']
