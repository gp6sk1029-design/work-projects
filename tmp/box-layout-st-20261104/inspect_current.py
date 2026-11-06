"""ST提案用に現行C版の箱詰め位置・カウント・設定コメントを確認する。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,re,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104C.smc2')
names=['Box_Total_CT','HMI_RCON2_2_OUT_TargetPos','HMI_RCON2_3_OUT_TargetPos','HMI_RCON2_4_OUT_TargetPos','RCON2_2_OUT_TargetPos_mm','RCON2_3_OUT_TargetPos_mm','RCON2_4_OUT_TargetPos_mm']
def brief(row):
 out=[]
 for e in row.get('CLs',[]):
  item={k:v for k,v in e.items() if k in ['__type','Var','Name','Not','X','Y']}
  for io in ['In','Out']:
   if io in e:item[io]=[{k:v for k,v in p.items() if k in ['Arg','Var','Type']} for p in e[io] if p.get('__type')=='PRM']
  out.append(item)
 return out
with zipfile.ZipFile(src) as z:
 sections=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'})
 target=next(s for s in sections if s['name']=='BoxPacking_箱詰め')
 rows=[json.loads(l) for l in z.read(target['part']).decode('utf-8-sig').splitlines()]
 selected=[{'row':i,'comment':r.get('CMT',''),'elements':brief(r)} for i,r in enumerate(rows) if any(n in json.dumps(r) for n in names)]
 definitions=[];counters=[]
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if t.startswith('[SLWD'):
   for line in t.splitlines():
    m=re.search(r'(?:^|\t)N=([^\t]+)',line)
    if m and (m[1] in names or ('Pitch' in m[1]) or ('Box_' in m[1]) or ('BoxPacking' in m[1])):definitions.append({'part':n,'definition':line})
  elif 'Box_Total_CT' in t and t.lstrip().startswith('{'):
   sec=next((s['name'] for s in sections if s['part']==n),n)
   for i,line in enumerate(t.splitlines()):
    if 'Box_Total_CT' in line:
     r=json.loads(line);counters.append({'section':sec,'row':i,'comment':r.get('CMT',''),'elements':brief(r)})
 data={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'target':target,'selected':selected,'definitions':definitions,'counter_rows':counters}
 (b/'inspection.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(data,ensure_ascii=False))
