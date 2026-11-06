from pathlib import Path
import json
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
for s in d['sections']:
 if s['name']=='RCON_IAI':
  for i,r in enumerate(s['rows']):
   if 320<=i<=329 or i>=443:
    print(i,json.dumps(r,ensure_ascii=False)[:11000])
 print('ORDER',s['name'])
