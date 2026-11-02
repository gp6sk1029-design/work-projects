"""利用者が保存し直した最新I版を、以前の作業用コピーと混同せず調査する。"""
from pathlib import Path
import collections
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261029I.smc2')
texts={};ladders={};tables={}
with zipfile.ZipFile(SOURCE) as z:
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if '\x00' in t:continue
  texts[n]=t
  if t.startswith('[SLWD'):
   tables[n]=[dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in t.splitlines() if l.startswith('++D=')]
  elif t.lstrip().startswith('{'):
   try:rows=[json.loads(l) for l in t.splitlines() if l.strip()]
   except:continue
   if rows and all('CLs' in r for r in rows):ladders[n]=rows
oem_name=next(n for n in texts if n.endswith('.oem'))
root=ET.fromstring(texts[oem_name]);parent={c:p for p in root.iter() for c in p}
names={};programs={}
for e in root.iter('Entity'):
 if e.get('type')=='Program':
  print('PROGRAM',e.get('name'),e.get('id'))
  programs[e.get('name')]={'id':e.get('id'),'children':[(x.get('type'),x.get('name'),x.get('id')) for x in e.find('ChildEntities')]}
 if e.get('type')=='PouBody' and e.get('subtype')=='Ladder':
  name=next((n for n in ladders if n.endswith(e.get('id')+'.xml')),None)
  if name:
   names[e.get('name')]=name
   print('SECTION',e.get('name'),name,len(ladders[name]))
   for i,r in enumerate(ladders[name]):
    outputs=[(c.get('__type'),c.get('Var'),c.get('Name'),[(p.get('Arg'),p.get('Var')) for p in c.get('Out',[]) if p.get('Var')]) for c in r['CLs'] if c.get('__type') in ('ST','F','FB','IST')]
    print('ROW',i,repr(r.get('CMT','')),outputs)
for n,t in tables.items():
 print('TABLE',n,[(p.get('N'),p.get('G'),p.get('D')) for p in t if p.get('N','').startswith(('Error_ST7','HMI_Message_Request','ST7_A_Dis2_M'))])
result={'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'texts':texts,'ladders':ladders,'tables':tables,'names':names,'programs':programs,'oem_name':oem_name}
(BASE/'inspection.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
print('SOURCE',result['sha256'],'SECTIONS',len(ladders),'RUNGS',sum(map(len,ladders.values())))
