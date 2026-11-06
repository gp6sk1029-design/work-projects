"""指令コイルの重複を分離し、受信側の並列接点を同時に追加する。"""
from pathlib import Path
from copy import deepcopy,copy
from lxml import etree as E
import zipfile,json,re,hashlib,io,sys,time
sys.stdout.reconfigure(encoding='utf-8')
start=time.monotonic();b=Path(__file__).parent
norm=json.loads((b/'C版修正検証.json').read_text(encoding='utf-8'))
file=Path(norm['output']);before=file.read_bytes()
assert hashlib.sha256(before).hexdigest()==norm['output_sha256'],'C版が外部更新されたため停止'
rename={9:('Out_CYw_Sep_Claw_F_Auto[2]','Out_CYw_Sep_Claw_F_Auto[4]'),13:('Out_CYw_Sep_Claw_H_Auto[1]','Out_CYw_Sep_Claw_H_Auto[2]'),12:('RCON2_1_Auto[2]','RCON2_1_Auto[5]'),15:('RCON2_1_Auto[3]','RCON2_1_Auto[6]')}
sections={};changes=[];topology=[]
def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def add_parallel(row,prefix,new_names):
 original=deepcopy(row)
 autos=[e for e in row['CLs'] if e.get('__type')=='LD' and e.get('Var','').startswith(prefix+'[')]
 assert autos and [e.get('Y',0) for e in autos]==list(range(len(autos)))
 assert all(e.get('X',0)==0 and not e.get('Not',False) for e in autos)
 assert not any(e.get('Var') in new_names for e in row['CLs'])
 count=len(autos);delta=len(new_names)
 shift=any(e.get('X',0)==0 and e.get('Y',0)>=count for e in row['CLs'])
 maxix=max([row['LRI'],row['RRI']]+[x.get('Ix',0) for x in walk(row)])
 if shift:
  for el in row['CLs']:
   if el.get('Y',0)>=count:el['Y']=el.get('Y',0)+delta
  new_vls=[]
  for v in row.get('VLs',[]):
   y=v.get('Y',0);v2=deepcopy(v)
   if y>=count:v2['Y']=y+delta
   new_vls.append(v2)
   if y==count-1:
    for j in range(1,delta+1):
     extra=deepcopy(v);extra['Y']=y+j;new_vls.append(extra)
  row['VLs']=new_vls
 insertion=row['CLs'].index(autos[-1])+1
 added=[]
 for j,name in enumerate(new_names):
  maxix+=1;el={'__type':'LD','Ix':maxix,'Var':name,'Y':count+j}
  row['CLs'].insert(insertion+j,el);added.append(el)
 merge=[v for v in row.get('VLs',[]) if v.get('X',0)==1 and v.get('Y',0)<count-1]
 if count>1:
  assert {v.get('Y',0) for v in merge}==set(range(count-1))
  assert len({v['Ix'] for v in merge})==1
  mergeix=merge[0]['Ix']
 else:maxix+=1;mergeix=maxix
 for y in range(count-1,count+delta-1):
  v={'Ix':mergeix,'X':1}
  if y:v['Y']=y
  row.setdefault('VLs',[]).append(v)
 assert {v.get('Y',0) for v in row['VLs'] if v['Ix']==mergeix}==set(range(count+delta-1))
 # 新接点を除去し座標挿入を戻せば、元の全命令に一致することを確認する。
 remaining=[e for e in row['CLs'] if e not in added]
 if shift:
  for el in remaining:
   if el.get('Y',0)>=count+delta:el['Y']-=delta
 assert remaining==original['CLs']
 # 逆変換チェックで座標を戻したため、保存する座標へもう一度移す。
 if shift:
  for el in remaining:
   if el.get('Y',0)>=count:el['Y']+=delta
 ids=[x['Ix'] for el in row['CLs'] for x in walk(el) if 'Ix' in x]
 assert len(ids)==len(set(ids))
 assert not ({row['LRI'],row['RRI']} & set(ids))
 assert not ({x['Ix'] for x in row['VLs']} & set(ids))
 topology.append({'prefix':prefix,'added':new_names,'original_parallel_count':count,'new_parallel_count':count+delta,'shifted_lower_rows':shift,'new_contact_ids':[e['Ix'] for e in added],'merge_vertical_id':mergeix})
with zipfile.ZipFile(io.BytesIO(before)) as z:
 for n in z.namelist():
  if not n.endswith('.oem'):continue
  for e in E.fromstring(z.read(n)).iter():
   if e.get('name') in ['Destacker_段バラシ','Output_出力','RCON_IAI'] and e.get('type')=='PouBody':sections[e.get('name')]=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'
 assert len(sections)==3
 originals={s:z.read(p) for s,p in sections.items()}
 lines={s:raw.decode('utf-8-sig').splitlines(keepends=True) for s,raw in originals.items()}
 rows={s:[json.loads(l) for l in ls] for s,ls in lines.items()}
 baseline=deepcopy(rows)
 dest=rows['Destacker_段バラシ']
 for i,(old,new) in rename.items():
  match=[e for e in walk(dest[i]) if e.get('__type')=='ST' and e.get('Var')==old]
  assert len(match)==1
  match[0]['Var']=new;changes.append({'section':'Destacker_段バラシ','row':i,'old':old,'new':new})
 add_parallel(rows['Output_出力'][277],'Out_CYw_Sep_Claw_F_Auto',['Out_CYw_Sep_Claw_F_Auto[4]'])
 add_parallel(rows['Output_出力'][279],'Out_CYw_Sep_Claw_F_Auto',['Out_CYw_Sep_Claw_F_Auto[4]'])
 add_parallel(rows['Output_出力'][276],'Out_CYw_Sep_Claw_H_Auto',['Out_CYw_Sep_Claw_H_Auto[2]'])
 add_parallel(rows['RCON_IAI'][281],'RCON2_1_Auto',['RCON2_1_Auto[5]','RCON2_1_Auto[6]'])
 outcoils=[e['Var'] for e in walk(dest) if e.get('__type')=='ST']
 assert len(outcoils)==len(set(outcoils)),'段バラシのコイルに重複あり'
 assert [int(re.fullmatch(r'Destacker_M\[(\d+)\]',v)[1]) for v in outcoils if v.startswith('Destacker_M[')]==list(range(1,25))
 patches={}
 changed_rows={}
 for section,part in sections.items():
  data=[];changed_rows[section]=[]
  for i,(a,c,l) in enumerate(zip(baseline[section],rows[section],lines[section])):
   if a==c:data.append(l)
   else:
    changed_rows[section].append(i)
    ending='\r\n' if l.endswith('\r\n') else '\n' if l.endswith('\n') else ''
    data.append(json.dumps(c,ensure_ascii=False,separators=(',',':'))+ending)
  bom=b'\xef\xbb\xbf' if originals[section].startswith(b'\xef\xbb\xbf') else b''
  patches[part]=bom+''.join(data).encode('utf-8')
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w') as zout:
  zout.comment=z.comment
  for e in z.infolist():zout.writestr(copy(e),patches.get(e.filename,z.read(e.filename)))
 result=out.getvalue()
 with zipfile.ZipFile(io.BytesIO(result)) as check:
  assert check.testzip() is None and check.namelist()==z.namelist()
  assert set(n for n in z.namelist() if z.read(n)!=check.read(n))==set(sections.values())
  for s,p in sections.items():assert [json.loads(l) for l in check.read(p).decode('utf-8-sig').splitlines()]==rows[s]
 assert file.read_bytes()==before,'C版が作業中に変更されたため停止'
 temporary=file.with_suffix('.smc2.codex-tmp')
 assert not temporary.exists()
 with temporary.open('xb') as f:f.write(result)
 assert temporary.read_bytes()==result
 temporary.replace(file)
 report={'source_B':norm['source'],'source_B_sha256':norm['source_sha256'],'output':str(file),'prior_C_sha256':norm['output_sha256'],'final_C_sha256':hashlib.sha256(result).hexdigest(),'command_renames':changes,'new_contacts':topology,'changed_rows':changed_rows,'changed_parts':list(sections.values()),'untouched_parts_vs_B':len(z.namelist())-3,'Destacker_coils_total':len(outcoils),'Destacker_coil_duplicates':[],'seconds':round(time.monotonic()-start,3),'native_Sysmac_build':'未実施'}
 (b/'C版指令重複修正.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
