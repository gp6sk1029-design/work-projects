"""SF排出の位置選択、カウンター、位置設定の定義を読み取り確認する。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,re,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104A.smc2')
def short(row):
 result=[]
 for e in row.get('CLs',[]):
  d={k:v for k,v in e.items() if k in ['__type','Ix','Var','Not','S','R','X','Y','Name']}
  for io in ['In','Out']:
   if io in e:d[io]=[{k:v for k,v in p.items() if k in ['__type','Var','Arg','Type']} for p in e[io]]
  result.append(d)
 return result
with zipfile.ZipFile(src) as z:
 assert z.testzip() is None
 sections=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml','subtype':e.get('subtype')})
 targets=[s for s in sections if s['name']=='ST7_A_Dis2_左SF排出'];assert len(targets)==1
 target=targets[0];rows=[json.loads(l) for l in z.read(target['part']).decode('utf-8-sig').splitlines()]
 view=[]
 for i,row in enumerate(rows):
  t=json.dumps(row,ensure_ascii=False)
  if any(x in t for x in ['A_SF_CT','HMI_RCON1_5_OUT_TargetPos','RCON1_5_OUT_TargetPos_mm']):view.append({'row':i,'comment':row.get('CMT',''),'elements':short(row)})
 defs=[];related=[];initial=[]
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if t.startswith('[SLWD'):
   for line in t.splitlines():
    if any('\tN='+name+'\t' in line for name in ['A_SF_CT','HMI_RCON1_5_OUT_TargetPos','RCON1_5_OUT_TargetPos_mm']):defs.append({'part':n,'definition':line})
  if n!=target['part'] and 'A_SF_CT' in t:
   if t.lstrip().startswith('{'):
    rr=[json.loads(l) for l in t.splitlines() if l.strip()]
    sec=next((s['name'] for s in sections if s['part']==n),n)
    for i,r in enumerate(rr):
     if 'A_SF_CT' in json.dumps(r):related.append({'section':sec,'row':i,'comment':r.get('CMT',''),'elements':short(r)})
  if 'HMI_RCON1_5_OUT_TargetPos' in t and not t.startswith('[SLWD') and not t.lstrip().startswith('{'):
   matches=list(re.finditer('HMI_RCON1_5_OUT_TargetPos',t))
   initial.extend({'part':n,'sample':t[max(0,m.start()-150):m.end()+300]} for m in matches[:4])
 data={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'parts':len(z.namelist()),'sections':sections,'target':target,'row_count':len(rows),'view':view,'definitions':defs,'related_counter':related,'other_position_data':initial}
 (b/'inspection.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 (b/'section_before.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in data.items() if k not in ['sections','other_position_data']},ensure_ascii=False))
 print('OTHER_POSITION_DATA',json.dumps(initial,ensure_ascii=False))
