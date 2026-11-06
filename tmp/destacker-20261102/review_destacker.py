"""段番号の重複と変更候補を読み取り専用で整理する。"""
from pathlib import Path
import json,zipfile,re,collections,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
info=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
with zipfile.ZipFile(info['source']) as z:
 target=next(h['part'] for h in info['hits'] if h['part'].endswith('fb95842e-fdb2-46b7-9a81-473d52d66cbf.xml'))
 rows=[json.loads(s) for s in z.read(target).decode('utf-8-sig').splitlines() if s.strip()]
 def elems(x):
  if isinstance(x,dict):
   if 'Var' in x: yield {k:v for k,v in x.items() if k in ['__type','Ix','X','Y','Var','Not']}
   for v in x.values():yield from elems(v)
  elif isinstance(x,list):
   for v in x:yield from elems(v)
 result=[]
 for i,r in enumerate(rows):
  el=list(elems(r));coils=[v['Var'] for v in el if v.get('__type') in ['ST','STN','S','R'] and v['Var'].startswith('Destacker_M[')]
  result.append({'表示行':i,'コイル':coils,'7行目以降の候補':[re.sub(r'\[(\d+)\]',lambda m:'['+str(int(m[1])+4)+']',v) for v in coils] if i>=7 else [],'接点と命令':el})
 other=[]
 for h in info['hits']:
  if h['part']==target:continue
  t=z.read(h['part']).decode('utf-8-sig')
  refs=re.findall(r'Destacker_M\s*\[\d+\]',t)
  if refs: other.append({'part':h['part'],'refs':dict(collections.Counter(refs))})
 (b/'行別確認.json').write_text(json.dumps({'対象':target,'行別':result,'対象外添字参照':other},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'行別コイル':[{k:v for k,v in r.items() if k!='接点と命令'} for r in result],'対象外添字参照':other,'7行目詳細':result[7]},ensure_ascii=False))
