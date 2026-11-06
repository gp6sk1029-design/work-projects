"""コメント追記対象の実際の回路と変数定義を読み取り確認する。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,re,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
p=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261103C.smc2')
def walk(x):
 if isinstance(x,dict):
  if 'Var' in x:yield {k:v for k,v in x.items() if k in ['__type','Var','Not','S','R','Arg','Y','X']}
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
with zipfile.ZipFile(p) as z:
 sec={}
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('name') in ['Destacker_段バラシ','Output_出力','RCON_IAI'] and e.get('type')=='PouBody':sec[e.get('name')]=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'
 rows={s:[json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines()] for s,n in sec.items()}
 dest=rows['Destacker_段バラシ']
 view=[{'row':i,'comment':r.get('CMT'),'variables':list(walk(r))} for i,r in enumerate(dest)]
 print('DESTACKER',json.dumps(view,ensure_ascii=False))
 keys={re.sub(r'\[\d+\]','',v['Var']) for r in dest for v in walk(r) if v['Var']}
 definitions=[]
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if t.startswith('[SLWD'):
   for line in t.splitlines():
    m=re.search(r'(?:^|\t)N=([^\t]+)',line)
    if m and m[1] in keys:definitions.append({'part':n,'line':line})
 print('DEFINITIONS',json.dumps(definitions,ensure_ascii=False))
 view2={s:[{'row':i,'comment':r.get('CMT'),'variables':list(walk(r))} for i,r in enumerate(rs) if (s=='Output_出力' and 268<=i<=279) or(s=='RCON_IAI' and 266<=i<=282)] for s,rs in rows.items() if s!='Destacker_段バラシ'}
 (b/'コメント追加前調査.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sections':sec,'destacker':view,'receivers':view2,'definitions':definitions},ensure_ascii=False,indent=2),encoding='utf-8')
 print('RECEIVERS',json.dumps(view2,ensure_ascii=False))
