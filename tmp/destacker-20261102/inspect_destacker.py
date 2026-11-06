"""指定原本を変更せず、段バラシのセクションと添字参照を調べる。"""
from pathlib import Path
import zipfile, json, re, hashlib, sys
sys.stdout.reconfigure(encoding='utf-8')
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261102A.smc2')
base=Path(__file__).parent
print('SOURCE',src.name,src.stat().st_size,hashlib.sha256(src.read_bytes()).hexdigest())
def walk(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if k=='Var': yield x
   yield from walk(x)
 elif isinstance(v,list):
  for x in v: yield from walk(x)
with zipfile.ZipFile(src) as z:
 assert z.testzip() is None
 hits=[]
 for e in z.infolist():
  try: t=z.read(e).decode('utf-8-sig')
  except UnicodeError: continue
  if '\x00' in t: continue
  if 'Destacker' in t:
   ms=list(re.finditer(r'Destacker(?:_段バラシ|_M)',t))
   hits.append({'part':e.filename,'count':len(ms),'samples':[t[max(0,m.start()-60):m.end()+100] for m in ms[:4]]})
   if t.lstrip().startswith('{'):
    rows=[json.loads(l) for l in t.splitlines() if l.strip()]
    found=[{'json_row':i,'type':r.get('_type'),'vars':list(walk(r)),'CMT':r.get('CMT'),'keys':list(r)} for i,r in enumerate(rows) if 'Destacker_M' in json.dumps(r,ensure_ascii=False)]
    print('LADDER',e.filename,len(rows),json.dumps(found,ensure_ascii=False))
    (base/'target_candidate.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print('HITS',json.dumps(hits,ensure_ascii=False))
 (base/'inspection.json').write_text(json.dumps({'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'hits':hits},ensure_ascii=False,indent=2),encoding='utf-8')
