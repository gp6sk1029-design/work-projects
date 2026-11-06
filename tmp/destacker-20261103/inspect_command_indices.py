"""新しい指令添字の使用状況と配列範囲を全ソースで調べる。"""
from pathlib import Path
from lxml import etree as E
import json,zipfile,re,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
d=json.loads((b/'C版修正検証.json').read_text(encoding='utf-8'))
prefixes=['Out_CYw_Sep_Claw_F_Auto','Out_CYw_Sep_Claw_H_Auto','RCON2_1_Auto']
def walk(x):
 if isinstance(x,dict):
  if x.get('__type')=='ST' and any(x.get('Var','').startswith(p+'[') for p in prefixes):yield x['Var']
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
with zipfile.ZipFile(d['output']) as z:
 names={}
 for n in z.namelist():
  if not n.endswith('.oem'):continue
  for e in E.fromstring(z.read(n)).iter():
   if e.get('subtype')=='Ladder' and e.get('type')=='PouBody':names[n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml']=e.get('name')
 writers=[];defs=[]
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if t.lstrip().startswith('{'):
   for i,line in enumerate(t.splitlines()):
    if line.strip():
     for v in walk(json.loads(line)):writers.append({'section':names.get(n,n),'row':i,'var':v})
  if t.startswith('[SLWD'):
   for line in t.splitlines():
    if any('\tN='+p+'\t' in line for p in prefixes):defs.append({'part':n,'definition':line})
 print(json.dumps({'writers':writers,'definitions':defs},ensure_ascii=False))
 (b/'指令添字使用状況.json').write_text(json.dumps({'writers':writers,'definitions':defs},ensure_ascii=False,indent=2),encoding='utf-8')
