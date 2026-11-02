"""今回指定されたE版の回路・宣言・メタ情報を読み取り確認する。"""
from pathlib import Path
import collections,hashlib,json,re,sys,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SRC=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261029E.smc2')
texts={};tables={};ladders={}
def walk(v):
 if isinstance(v,dict):
  yield v
  for x in v.values():yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)
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
names={k:next(n for n in texts if n.endswith(suffix)) for k,suffix in {'error':'78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml','st7':'1c62506a-fffa-4120-bf30-bcfd518c76f9.xml','globals':'f07dd06c-505c-431b-b9fc-098949805b4e.xml','mode_vars':'b530d740-9d69-41c3-974a-97c06e823eb2.xml','movement_vars':'86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml','metadata':'20a6b651-4c34-401a-965e-db3e18414d5c.xml'}.items()}
for i,row in enumerate(ladders[names['error']]):
 print('ERROR_ROW',i,'CMT',repr(row.get('CMT')),'CELLS',[(x.get('__type'),x.get('Name'),x.get('Var'),x.get('Not')) for x in row['CLs']])
 if i in (11,12,16,17,22):print('FULL_ROW',i,json.dumps(row,ensure_ascii=False))
for i,row in enumerate(ladders[names['st7']]):
 if any(x.get('Var')=='ST7_A_Dis2_M[11]' and x.get('__type')=='ST' for x in walk(row)):
  print('ST7_CAUSE',i,json.dumps(row,ensure_ascii=False))
for n,table in tables.items():
 for p in table:
  if p['N'] in ('Error_M','Error_TON') or p['N'].startswith('RCON1_1_IN_') and p['N'].endswith(('Alarm','EmergencyStop')):print('DECL',n,p)
print('MODE_HEADER',repr(texts[names['mode_vars']][:400]))
print('GLOBAL_HEADER',repr(texts[names['globals']][:350]))
print('HASH',hashlib.sha256(SRC.read_bytes()).hexdigest(),'ENTRIES',len(texts),'RUNGS',sum(map(len,ladders.values())))
(BASE/'inspection.json').write_text(json.dumps({'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'texts':texts,'tables':tables,'ladders':ladders,'names':names},ensure_ascii=False),encoding='utf-8')
