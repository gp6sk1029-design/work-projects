from pathlib import Path
from zipfile import ZipFile
import json,hashlib,re
from lxml import etree as E
p=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104C.smc2')
print('HASH',hashlib.sha256(p.read_bytes()).hexdigest())
with ZipFile(p) as z:
 sections=[]
 for name in z.namelist():
  if name.endswith('.oem'):
   for e in E.fromstring(z.read(name)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':name.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'})
 targets=[s for s in sections if s['name']=='BoxPacking_箱詰め'];assert len(targets)==1
 n=targets[0]['part'];print('TARGET',n)
 rows=[json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines()]
 print('ROWS',len(rows))
 for i in range(25,len(rows)):print('ROW',i,json.dumps(rows[i],ensure_ascii=False))
 count=0
 for n in z.namelist():
  if not n.endswith('.xml'):continue
  t=z.read(n).decode('utf-8-sig',errors='replace')
  if '"__type":"IST"' in t:
   for i,l in enumerate(t.splitlines()):
    if '"__type":"IST"' in l:
     r=json.loads(l)
     if not any(e.get('__type')=='ST' for e in r['CLs']):continue
     for e in r['CLs']:
      if e['__type']=='IST' and len(e.get('TXT',''))>1200:e['TXT']=e['TXT'][:500]+'...'
     if count<3:print('IST_WITH_COIL',n,i,json.dumps(r,ensure_ascii=False));count+=1
  if 'Box_Total_CT' in t and t.lstrip().startswith('{'):
   for i,l in enumerate(t.splitlines()):
    if 'Box_Total_CT' in l:print('COUNTER_ROW',n,i,l[:4500])
 for n in z.namelist():
  t=z.read(n).decode('utf-8-sig',errors='replace')
  if t.startswith('[SLWD') and ('N=Box_Total_CT\t' in t or 'N=BoxPacking_M\t' in t):
   print('VARTABLE',n)
   for l in t.splitlines():
    if 'BoxPacking_M' in l or 'Box_Total_CT' in l or 'N=HMI_RCON2_2_OUT_TargetPos\t' in l:print(l[:1800])
