"""段バラシの外向きコイルと出力・RCON側の接点を読む。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,re,sys,hashlib
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
info=json.loads((b/'B版番号確認.json').read_text(encoding='utf-8'))
src=Path(info['file']);assert hashlib.sha256(src.read_bytes()).hexdigest()==info['sha256']
def walk(x,path):
 if isinstance(x,dict):
  if 'Var' in x:yield {'path':path,**{k:v for k,v in x.items() if k in ['__type','Ix','X','Y','Var','Not']}}
  for k,v in x.items():yield from walk(v,path+[k])
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from walk(v,path+[i])
with zipfile.ZipFile(src) as z:
 sections=[]
 for n in z.namelist():
  if not n.endswith('.oem'):continue
  root=E.fromstring(z.read(n));folder=n.rsplit('/',1)[0]
  for el in root.iter():
   if el.get('subtype')=='Ladder':sections.append({'name':el.get('name'),'part':folder+'/'+el.get('id')+'.xml'})
 print('SECTIONS',json.dumps(sections,ensure_ascii=False))
 dest=[json.loads(l) for l in z.read(info['target']).decode('utf-8-sig').splitlines() if l.strip()]
 outgoing=[p for p in walk(dest,[]) if p.get('__type')=='ST' and not p['Var'].startswith('Destacker_M[')]
 names={p['Var'] for p in outgoing}
 print('OUTGOING',json.dumps(outgoing,ensure_ascii=False))
 results=[]
 for s in sections:
  if not any(x in s['name'] for x in ['Output','出力','RCON_IAI']):continue
  text=z.read(s['part']).decode('utf-8-sig')
  rows=[json.loads(l) for l in text.splitlines() if l.strip()]
  els=list(walk(rows,[]));found=[]
  for p in els:
   if p['Var'] in names:found.append(p)
  related=[p for p in els if isinstance(p['Var'],str) and (p['Var'].startswith('Out_CYw_') or p['Var'].startswith('RCON2_1_Auto['))]
  results.append({**s,'row_count':len(rows),'exact_matches':found,'related':related})
  (b/(s['name'].replace('/','_')+'_参照.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print('MATCHES',json.dumps([{k:v for k,v in r.items() if k!='related'} for r in results],ensure_ascii=False))
 (b/'routes_inspection.json').write_text(json.dumps({'source':str(src),'sha256':info['sha256'],'sections':sections,'outgoing':outgoing,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
 print('DESTACKER_ROWS_3_6',json.dumps(dest[3:7],ensure_ascii=False))
