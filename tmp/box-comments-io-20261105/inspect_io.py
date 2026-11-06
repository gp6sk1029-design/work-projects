"""コメント案に使う実入出力・RCON軸を実ファイルから調べる。"""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,re
b=Path(__file__).parent
m=json.loads((b.parent/'box-order-F-20261105/verification.json').read_text(encoding='utf-8'))
with ZipFile(m['source']) as z:
 sections=[];defs={}
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody':sections.append((e.get('name'),n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'))
  t=z.read(n).decode('utf-8-sig',errors='replace')
  if t.startswith('[SLWD'):
   for l in t.splitlines():
    if l.startswith('++D='):
     d=dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p);defs.setdefault(d['N'],[]).append(d)
 box=[json.loads(l) for l in z.read(m['box_part']).decode('utf-8-sig').splitlines()]
 used={c.get('Var','') for r in box for c in r['CLs'] if c.get('__type')=='LD'}
 sensors={v for v in used if v.startswith('TimerQ_')}
 targets={v for v in used if v.startswith('Out_') and v.endswith('_Done')}
 for name,p in sections:
  if name not in ['Input_入力','Output_出力']:continue
  rr=[json.loads(l) for l in z.read(p).decode('utf-8-sig').splitlines()]
  for i,r in enumerate(rr):
   text=json.dumps(r)
   if name.startswith('Input') and any(v in text for v in sensors):print('INPUT',i,json.dumps(r,ensure_ascii=False))
   if name.startswith('Output') and (any(v in text for v in targets) or any(v.replace('_Done','')==c.get('Var') for v in targets for c in r['CLs'] if c['__type']=='ST')):print('OUTPUT',i,json.dumps(r,ensure_ascii=False))
 for n,ds in defs.items():
  if any(k in n for k in ['Ejc_Cont','Box_Chuck','Container_Arrival','Container_Pass','Tray_Direction','Empty_Container_CY_H']) or re.fullmatch(r'RCON2_[2345]_OUT_TargetPos_mm',n):print('DEF',n,json.dumps(ds[0],ensure_ascii=False))
 (b/'definitions.json').write_text(json.dumps(defs,ensure_ascii=False),encoding='utf-8')
