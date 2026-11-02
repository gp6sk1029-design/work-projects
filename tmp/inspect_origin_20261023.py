"""指定B版の宣言・原点復帰ラダーと参照先を読み取り調査する。"""
from pathlib import Path
from zipfile import ZipFile
import sys,re,json,hashlib,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
src=next(Path(r'C:\Users\SEIGI-N13\Desktop').glob('3089-2603A_*_20261023B.smc2'))
out=Path(__file__).with_suffix('.txt')
lines=['SOURCE '+str(src),'SHA256 '+hashlib.sha256(src.read_bytes()).hexdigest()]
with ZipFile(src) as z:
 data={n:z.read(n) for n in z.namelist()}
 text={}
 for n,b in data.items():
  try:text[n]=b.decode('utf-8-sig')
  except UnicodeError:pass
 oem=next(t for n,t in text.items() if n.endswith('.oem'))
 root=ET.fromstring(oem)
 names={e.get('id'):e.get('name') for e in root.iter('Entity')}
 for n,b in data.items():
  if b'_Swv_' in b or b'\x00_\x00S\x00w\x00v\x00_' in b:
   lines.append('HIT '+n+' TEXT='+str(n in text)+' ASCII='+str(b.count(b'_Swv_')))
 for n,t in text.items():
  if t.startswith('[SLWD'):
   hits=[l for l in t.splitlines() if re.search(r'Swv|Rev|Origin|Auto_[AB]_Start|TimerQ_In_Sen_Work_[AB]_Pos_0[46]',l)]
   if hits:lines.extend(['\nDECL '+n]+hits)
  elif t.lstrip().startswith('{'):
   rungs=[json.loads(l) for l in t.splitlines() if l.strip()]
   name=names.get(Path(n).stem,'?')
   if name.startswith('Origin') or any('ST4_A_Rev_01_Origin_M' in json.dumps(r) for r in rungs):
    lines.append('\nFULL LADDER '+n+' NAME='+name)
    for i,r in enumerate(rungs):lines.append('RUNG '+str(i)+' '+json.dumps(r,ensure_ascii=False))
   else:
    selected=[]
    for i,r in enumerate(rungs):
     if re.search(r'Swv|Rev|Origin_Busy|Origin_End',json.dumps(r,ensure_ascii=False)):
      selected.append('RUNG '+str(i)+' '+json.dumps(r,ensure_ascii=False))
    if selected:lines.extend(['\nRELATED LADDER '+n+' NAME='+name]+selected)
 lines.append('\nOEM MATCHES')
 for l in oem.splitlines():
  if re.search(r'Swv|Rev|Origin',l):lines.append(l)
out.write_text('\n'.join(lines),encoding='utf-8')
print(str(out),len(lines),'lines',out.stat().st_size,'bytes')
print('\n'.join(lines[:30]))
