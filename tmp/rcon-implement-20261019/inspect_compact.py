from pathlib import Path
import json,sys,xml.etree.ElementTree as ET,re
sys.stdout.reconfigure(encoding='utf8')
d=json.loads((Path(__file__).parent/'inspection.json').read_text(encoding='utf8')); texts=d['texts']
r=ET.fromstring(texts[d['oem']]); parents={c:p for p in r.iter() for c in p}
ids=['7b1666c7-ee97-4210-81b2-fed5a6172074','a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10','98de6707-f996-4f77-aad9-b0569299efb5','76d6fc6a-f4a4-46b3-8891-ff16aa25214c','5455357b-f8f7-4b15-b825-2ceca787a3f2','34f6688b-dff7-4c01-860e-34378fd27b9c','c58a0379-e2dd-4728-9169-d233109e2594']
for id in ids:
 e=next((e for e in r.iter('Entity') if e.get('id')==id),None)
 if e is not None:print('ENTITY',ET.tostring(e,encoding='unicode'))
 for n,t in texts.items():
  if n.endswith('/'+id+'.xml'):print('FILE',n,'\n',t)
gt=next(t for t in texts.values() if '+GN=VAR_GLOBAL' in t)
for pattern in [r'\bN=RCON[12]_[^\t]+',r'\bN=E005_',r'\bN=E001_']:
 lines=[l for l in gt.splitlines() if re.search(pattern,l)]
 print('GLOBAL',pattern,len(lines),'\n'+'\n'.join(lines if 'RCON' in pattern else lines[:3]+lines[-3:]))
for n,t in texts.items():
 if n.endswith('/4bdcdc10-734d-4589-b299-075e93db9b10.xml'):
  tr=ET.fromstring(t)
  for e in tr.iter('DataType'):
   if (e.get('Name') or '').startswith('ST_RCON'):print('TYPE',ET.tostring(e,encoding='unicode'))
print('INLINE OEM EXCERPT')
t=texts[d['oem']]; i=t.find('id="76d6fc6a-f4a4-46b3-8891-ff16aa25214c"'); print(t[i-180:i+500])
