"""E版のI/Oコメントと所属候補を読み取り調査する。"""
from pathlib import Path
import collections,hashlib,json,re,sys,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SRC=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261029E.smc2')
texts={};tables={};ladders={}
with zipfile.ZipFile(SRC) as z:
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if '\x00' in t:continue
  texts[n]=t
  if t.startswith('[SLWD'):
   tables[n]=[dict(x.split('=',1) for x in l[2:].split('\t') if '=' in x) for l in t.splitlines() if l.startswith('++D=')]
  elif t.lstrip().startswith('{'):
   try:rr=[json.loads(l) for l in t.splitlines() if l.strip()]
   except Exception:continue
   if rr and all('CLs' in r for r in rr):ladders[n]=rr
gname=next(n for n,t in texts.items() if t.startswith('[SLWD') and '+GN=VAR_GLOBAL' in t)
g={p['N']:p for p in tables[gname]}
io=[p for p in g.values() if re.search(r'【[XY][0-9A-F]+】',p.get('Com',''))]
for p in io:
 print('KNOWN' if re.search(r'\bST\d',p['Com']) else 'MISSING',p['N'],p['Com'])
print('SUMMARY',len(io),'withoutST',sum(not bool(re.search(r'\bST\d',p['Com'])) for p in io),'hash',hashlib.sha256(SRC.read_bytes()).hexdigest())
data={'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'texts':texts,'tables':tables,'globals_name':gname,'io':io,'ladder_counts':{n:len(rr) for n,rr in ladders.items()}}
(BASE/'inspection.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
