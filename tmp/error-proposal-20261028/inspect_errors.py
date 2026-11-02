"""エラー処理の現行構成と全参照を読み取り専用で調査する。"""
from pathlib import Path
import collections,hashlib,json,re,sys,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SRC=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261029F.smc2')
texts={};tables={};ladders={};refs=collections.defaultdict(list)
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
   try:rows=[json.loads(l) for l in t.splitlines() if l.strip()]
   except Exception:continue
   if rows and all('CLs' in row for row in rows):ladders[n]=rows
for n,rr in ladders.items():
 for i,row in enumerate(rr):
  tokens=[];writes=[]
  for node in walk(row):
   v=node.get('Var');txt=node.get('TXT')
   if v and 'Error_M' in v:
    refs[v].append({'entry':n,'row':i,'type':node.get('__type')});tokens.append((node.get('__type'),v))
   if node.get('__type') in ('ST','STs','STr') and v:writes.append(v)
  if tokens:
   variables=sorted({x.get('Var') for x in walk(row) if x.get('Var')})
   print('ROW',Path(n).stem,i,'CMT',row.get('CMT'),'ERRORS',tokens,'VARS',variables)
for n,table in tables.items():
 for p in table:
  if p['N']=='Error_M':print('ERROR_DECL',Path(n).stem,p)
for n,t in texts.items():
 if t.lstrip().startswith('<'):
  for m in re.finditer('Error_エラー処理',t):print('SECTION_CONTEXT',n,t[max(0,m.start()-230):m.end()+180])
print('HASH',hashlib.sha256(SRC.read_bytes()).hexdigest(),'ERROR_REF_COUNTS',{k:len(v) for k,v in refs.items()})
(BASE/'inspection.json').write_text(json.dumps({'source':str(SRC),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'texts':texts,'tables':tables,'ladders':ladders,'references':dict(refs)},ensure_ascii=False),encoding='utf-8')
