"""複製に必要なラダーと登録情報の形を確認する。"""
from pathlib import Path
import json, sys, re, xml.etree.ElementTree as E
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).resolve().parent;d=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
rows=json.loads((b/'rcon_rows.json').read_text(encoding='utf-8'))
for i in (203,208,209,210,211,212,222,223,240,241,242):
 print('ROW',i,json.dumps(rows[i],ensure_ascii=False))
for n,t in d['texts'].items():
 if n.endswith('manifest') or n.endswith('.oem'):
  print('IDENTITY',n,t[:1100])
 if t.startswith('[SLWD') and 'N=RCON1_6_TON' in t:
  print('LOCAL_TAIL',n,t[-2400:])
 if t.lstrip().startswith('<') and '<Variable ' in t:
  root=E.fromstring(t)
  print('META',n,root.tag,len(list(root.iter('Variable'))))
  for e in root.iter('Variable'):
   if e.get('Name') in ('RCON1_6_Auto','RCON1_6_M','RCON1_6_MoveDone','RCON1_6_OUT_TargetPos_mm','RCON2_OUT'):
    print(E.tostring(e,encoding='unicode')[:2000])
print('SOURCE_EXISTS',Path(d['source']).exists())
