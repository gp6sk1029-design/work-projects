"""現在版と履歴を読取り比較し、追加実変数とその参照を一覧化する。PLCファイルは変更しない。"""
from pathlib import Path
import collections,hashlib,json,re,sys,xml.etree.ElementTree as ET,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
ROOT=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON')
CURRENT=list((ROOT/'Codex編集用').glob('*.smc2'));assert len(CURRENT)==1
HISTORY=ROOT/'履歴'/'Codex_履歴'

def walk(v):
 if isinstance(v,dict):
  yield v
  for item in v.values():yield from walk(item)
 elif isinstance(v,list):
  for item in v:yield from walk(item)

def load(path):
 texts={};tables={};rows={};owners={}
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for n in z.namelist():
   try:t=z.read(n).decode('utf-8-sig')
   except UnicodeError:continue
   if '\x00' in t:continue
   texts[n]=t
  oem=ET.fromstring(next(t for n,t in texts.items() if n.endswith('.oem')))
  def visit(e,route):
   route=route+([e.get('name')] if e.get('name') else [])
   if e.get('id'):owners[e.get('id')]=' / '.join(route[-3:])
   for c in e:visit(c,route)
  visit(oem,[])
  for n,t in texts.items():
   leaf=n.rsplit('/',1)[-1].split('.',1)[0];owner=owners.get(leaf,leaf)
   if t.startswith('[SLWD'):
    for l in t.splitlines():
     if not l.startswith('++D='):continue
     p=dict(v.split('=',1) for v in l[2:].split('\t') if '=' in v)
     tables[(leaf,p['N'])]={**p,'owner':owner}
   elif t.startswith('{"CLs"'):
    rows[owner]=[json.loads(l) for l in t.splitlines() if l.strip()]
 return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'tables':tables,'rows':rows}

versions={}
for suffix in ('E','G','H','I','J','K','L','M','N'):
 paths=list(HISTORY.glob('*20261029'+suffix+'.smc2'))
 if paths:versions[suffix]=load(paths[0])
versions['O']=load(CURRENT[0])
base=versions['E'];cur=versions['O']
def actual(v):
 return {p['N']:p for p in v['tables'].values() if p.get('G')!='VAR_EXTERNAL'}
old=actual(base);now=actual(cur)
newnames=sorted(set(now)-set(old))
newvars=[]
for name in newnames:
 decl=now[name];usage=[]
 for owner,rr in cur['rows'].items():
  for i,r in enumerate(rr):
   nodes=[]
   for c in r['CLs']:
    for node in walk(c):
     var=node.get('Var','')
     if re.match(re.escape(name)+r'(?:\[|\.|$)',var):
      nodes.append({'kind':c['__type'],'node_kind':node.get('__type'),'var':var,'coil_set':c.get('S',False),'coil_reset':c.get('RS',False)})
   if nodes:usage.append({'section':owner,'row':i,'comment':r.get('CMT',''),'nodes':nodes})
 first=next((ver for ver,data in versions.items() if name in actual(data)),None)
 newvars.append({'name':name,'type':decl['D'],'scope':decl.get('G'),'owner':decl['owner'],'comment':decl.get('Com'),'first_version':first,'usage':usage})
changes=[]
for a,b in zip(list(versions),list(versions)[1:]):
 before=actual(versions[a]);after=actual(versions[b])
 changes.append({'transition':a+'→'+b,'new_actual_names':sorted(set(after)-set(before)),'removed_actual_names':sorted(set(before)-set(after)),'row_count':sum(map(len,versions[b]['rows'].values()))})
aux={'HMI_Error_WorkSample','Error_ST7_A_Source_M','Error_ST1_A_Timeout','Error_ST5_A_Timeout','HMI_Message_Request'}
requested={'Error_'+station+'_M' for station in ('ST1_A','ST1_B','ST2_A','ST3_A','ST4_A','ST5_A','ST5_B','ST6_A','ST7_A')}
assert set(newnames)==aux|requested
def fbs(data):return collections.Counter((c.get('Name'),c.get('Var')) for rr in data['rows'].values() for row in rr for c in row['CLs'] if c['__type']=='FB')
assert fbs(base)==fbs(cur),'既存FB実体/呼出し件数に別の変更あり'
removed={'Error_ST7_A_Sample_M','Error_Common_MessageActive'}
assert not (removed&set(now))
report={'current':cur['path'],'current_sha256':cur['sha256'],'baseline':base['path'],'baseline_sha256':base['sha256'],'versions':{k:{'path':v['path'],'sha256':v['sha256']} for k,v in versions.items()},'new_variables':newvars,'version_changes':changes,'classification':{'auxiliary_actual_variables':sorted(aux),'requested_station_error_arrays':sorted(requested),'new_actual_names_all_classified':True,'fb_instance_call_multiset_preserved':True,'already_removed_variables':sorted(removed)},'project_files_modified':False}
(BASE/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('CURRENT',cur['path'],'HASH',cur['sha256'])
print('NEW_ACTUAL_COUNT',len(newvars))
for v in newvars:
 uses=[(u['section'].rsplit(' / ',1)[-1],u['row']) for u in v['usage']]
 print(v['first_version'],v['scope'],v['name'],v['type'],'ROWS',uses[:12],'TOTAL',len(uses))
print('TRANSITIONS',json.dumps(changes,ensure_ascii=False))
# 現在のError/HMI/ST7の全行と参照を照合できる読取りダンプ。
lines=[]
for owner,rr in cur['rows'].items():
 if not owner.endswith(('Error_エラー処理','HMI','ST7_A_Dis2_左SF排出')):continue
 lines.append('\nSECTION '+owner)
 for i,r in enumerate(rr):
  lines.append(str(i)+' '+r.get('CMT','').replace('\r\n',' / ')+' '+str([(c.get('__type'),c.get('Name'),c.get('Var')) for c in r['CLs'] if c.get('Var') or c.get('Name')]))
(BASE/'rungs.txt').write_text('\n'.join(lines),encoding='utf-8')
assert hashlib.sha256(CURRENT[0].read_bytes()).hexdigest()==cur['sha256']
