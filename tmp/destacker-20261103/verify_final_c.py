"""B版と最終C版を再読込みして、連番・一意な指令・受信接点・分岐接続を検証する。"""
from pathlib import Path
from lxml import etree as E
from copy import deepcopy
import zipfile,json,re,collections,hashlib,sys,csv
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
fix=json.loads((b/'C版指令重複修正.json').read_text(encoding='utf-8'))
norm=json.loads((b/'C版修正検証.json').read_text(encoding='utf-8'))
source=Path(fix['source_B']);output=Path(fix['output']);m_changes=0;command_changes=0
renames={9:('Out_CYw_Sep_Claw_F_Auto[2]','Out_CYw_Sep_Claw_F_Auto[4]'),12:('RCON2_1_Auto[2]','RCON2_1_Auto[5]'),13:('Out_CYw_Sep_Claw_H_Auto[1]','Out_CYw_Sep_Claw_H_Auto[2]'),15:('RCON2_1_Auto[3]','RCON2_1_Auto[6]')}
def compare_dest(a,c,path):
 global m_changes,command_changes
 assert type(a)==type(c)
 if isinstance(a,dict):
  assert list(a)==list(c)
  for k in a:compare_dest(a[k],c[k],path+[k])
 elif isinstance(a,list):
  assert len(a)==len(c)
  for i in range(len(a)):compare_dest(a[i],c[i],path+[i])
 else:
  expected=a
  if path[-1]=='Var' and isinstance(a,str):
   m=re.fullmatch(r'Destacker_M\[(\d+)\]',a)
   if m:
    n=int(m[1]);mapping={**{i:i for i in range(1,6)},7:6,9:8,**{i:i-1 for i in range(10,26)}}
    if n==8:
     n2={(4,'CLs',2,'Var'):7,(4,'CLs',6,'Var'):7,(5,'CLs',0,'Var'):7,(5,'CLs',2,'Var'):8,(5,'CLs',6,'Var'):8}[tuple(path)]
    else:n2=mapping[n]
    expected=f'Destacker_M[{n2}]'
    if expected!=a:m_changes+=1
   elif path[0] in renames and a==renames[path[0]][0]:expected=renames[path[0]][1];command_changes+=1
  assert c==expected,(path,a,c,expected)
def elements(x,path):
 if isinstance(x,dict):
  yield {'path':path,**x}
  for k,v in x.items():yield from elements(v,path+[k])
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from elements(v,path+[i])
def verify_parallel(old,new,prefix,added,shift):
 count=len([x for x in old['CLs'] if x.get('__type')=='LD' and x.get('Var','').startswith(prefix+'[')])
 delta=len(added)
 news=[e for e in new['CLs'] if e.get('Var') in added]
 assert len(news)==delta
 assert {e['Var'] for e in news}==set(added)
 assert [e.get('Y',0) for e in news]==list(range(count,count+delta))
 assert all(e.get('__type')=='LD' and e.get('X',0)==0 and not e.get('Not',False) for e in news)
 existing=[deepcopy(e) for e in new['CLs'] if e not in news]
 if shift:
  for e in existing:
   if e.get('Y',0)>=count+delta:e['Y']-=delta
 assert existing==old['CLs'],'元の命令または共通条件が変化'
 assert {k:v for k,v in old.items() if k not in ['CLs','VLs']}=={k:v for k,v in new.items() if k not in ['CLs','VLs']}
 oldids={e.get('Ix') for e in elements(old,[]) if e.get('Ix') is not None}
 assert not oldids.intersection({e['Ix'] for e in news})
 expected=set()
 for e in old.get('VLs',[]):
  y=e.get('Y',0)
  p1=y+delta if shift and y>=count else y
  p2=y+1+delta if shift and y+1>=count else y+1
  for pos in range(p1,p2):expected.add((e['Ix'],e.get('X',0),pos))
 merge=[e for e in new['VLs'] if e.get('X',0)==1 and e.get('Y',0)<count+delta-1]
 assert len({e['Ix'] for e in merge})==1
 mergeid=merge[0]['Ix']
 assert {e.get('Y',0) for e in merge}==set(range(count+delta-1))
 expected.update((mergeid,1,y) for y in range(count-1,count+delta-1))
 actual={(e['Ix'],e.get('X',0),e.get('Y',0)) for e in new['VLs']}
 assert len(actual)==len(new['VLs']) and actual==expected,'分岐線の過不足'
 # 受信接点追加後も元のLRI/RRIと全命令の識別子が衝突しない。
 ids=[e['Ix'] for el in new['CLs'] for e in elements(el,[]) if 'Ix' in e]
 assert len(ids)==len(set(ids))
 assert not set(ids).intersection({new['LRI'],new['RRI']}|{e['Ix'] for e in new['VLs']})
with zipfile.ZipFile(source) as a,zipfile.ZipFile(output) as z:
 assert a.testzip() is None and z.testzip() is None and a.namelist()==z.namelist()
 section={}
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody' and e.get('name') in ['Destacker_段バラシ','Output_出力','RCON_IAI']:section[e.get('name')]=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'
 changed=[n for n in z.namelist() if z.read(n)!=a.read(n)]
 assert set(changed)==set(section.values())
 old={s:[json.loads(l) for l in a.read(p).decode('utf-8-sig').splitlines()] for s,p in section.items()}
 new={s:[json.loads(l) for l in z.read(p).decode('utf-8-sig').splitlines()] for s,p in section.items()}
 compare_dest(old['Destacker_段バラシ'],new['Destacker_段バラシ'],[])
 assert (m_changes,command_changes)==(53,4)
 specs=[('Output_出力',276,'Out_CYw_Sep_Claw_H_Auto',['Out_CYw_Sep_Claw_H_Auto[2]'],False),('Output_出力',277,'Out_CYw_Sep_Claw_F_Auto',['Out_CYw_Sep_Claw_F_Auto[4]'],True),('Output_出力',279,'Out_CYw_Sep_Claw_F_Auto',['Out_CYw_Sep_Claw_F_Auto[4]'],False),('RCON_IAI',281,'RCON2_1_Auto',['RCON2_1_Auto[5]','RCON2_1_Auto[6]'],True)]
 for s in ['Output_出力','RCON_IAI']:
  allowed={r for sn,r,*_ in specs if sn==s}
  assert len(old[s])==len(new[s])
  for i in range(len(old[s])):
   if i not in allowed:assert old[s][i]==new[s][i]
 for s,r,prefix,added,shift in specs:verify_parallel(old[s][r],new[s][r],prefix,added,shift)
 es=list(elements(new['Destacker_段バラシ'],[]))
 coils=[e['Var'] for e in es if e.get('__type')=='ST']
 assert len(coils)==len(set(coils))==41
 stage=[int(re.fullmatch(r'Destacker_M\[(\d+)\]',v)[1]) for v in coils if v.startswith('Destacker_M[')]
 assert stage==list(range(1,25))
 contacts=[e['Var'] for e in es if e.get('__type')=='LD' and e.get('Var','').startswith('Destacker_M[')]
 assert set(contacts)<=set(coils)
 outgoing=[e for e in es if e.get('__type')=='ST' and (e.get('Var','').startswith('Out_') or e.get('Var','').startswith('RCON'))]
 assert len(outgoing)==len({e['Var'] for e in outgoing})==16
 routes=[]
 for e in outgoing:
  v=e['Var'];s='Output_出力' if v.startswith('Out_') else 'RCON_IAI'
  expect=v.split('_Auto[')[0] if s=='Output_出力' else 'RCON2_1_M[1]'
  drive=[];other=[]
  for item in elements(new[s],[]):
   if item.get('__type')=='LD' and item.get('Var')==v:
    assert not item.get('Not',False)
    r=item['path'][0]
    outputvars={x.get('Var') for x in elements(new[s][r],[]) if x.get('__type')=='ST'}
    (drive if expect in outputvars else other).append(r)
  assert drive,(v,'駆動側接点未接続')
  routes.append({'変数':v,'段バラシ行':e['path'][0],'接続先':s,'駆動接点行':sorted(set(drive)),'監視等接点行':sorted(set(other)),'駆動コイル':expect,'判定':'一致'})
 assert next(r for r in routes if r['変数']=='Out_CYw_Sep_Claw_F_Auto[4]')['監視等接点行']==[279]
 assert next(r for r in routes if r['変数']=='Out_CYw_Sep_Claw_H_Auto[2]')['監視等接点行']==[276]
 # 全ラダーの指令書込みと配列定義も照合する。
 writers=collections.Counter();bounds={}
 for n in z.namelist():
  try:text=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if text.lstrip().startswith('{'):
   for line in text.splitlines():
    if line.strip():
     for e in elements(json.loads(line),[]):
      if e.get('__type')=='ST' and e.get('Var') in {x['Var'] for x in outgoing}:writers[e['Var']]+=1
  if text.startswith('[SLWD'):
   for line in text.splitlines():
    m=re.search(r'D=ARRAY\[(\d+)\.\.(\d+)\] OF Bool\tN=([^\t]+)',line)
    if m:bounds.setdefault(m[3],set()).add((int(m[1]),int(m[2])))
 assert all(writers[e['Var']]==1 for e in outgoing)
 for e in outgoing:
  m=re.fullmatch(r'(.+)\[(\d+)\]',e['Var']);assert m and m[1] in bounds
  assert all(lo<=int(m[2])<=hi for lo,hi in bounds[m[1]])
 assert hashlib.sha256(source.read_bytes()).hexdigest()==fix['source_B_sha256']
 assert hashlib.sha256(output.read_bytes()).hexdigest()==fix['final_C_sha256']
 report={'file':str(output),'sha256':fix['final_C_sha256'],'stage_coils':stage,'stage_missing':[],'stage_duplicates':[],'all_Destacker_coil_count':41,'all_Destacker_duplicate_coils':[],'command_coils':16,'Output_routes':10,'RCON_routes':6,'unconnected_routes':[],'global_command_write_duplicates':[],'added_receiver_contacts':5,'parallel_graph_checks':4,'stage_reference_changes':m_changes,'command_reference_changes':command_changes,'unchanged_parts':len(z.namelist())-3,'B_original_unchanged':True,'array_bounds':'全16指令で適合','ZIP_CRC':'正常','native_Sysmac_build':'未実施','PLC接続と転送':'未実施','routes':routes}
 (b/'最終C版検証.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 with (b/'最終接点割付確認一覧.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(routes[0]));w.writeheader();w.writerows(routes)
 print(json.dumps({k:v for k,v in report.items() if k!='routes'},ensure_ascii=False))
