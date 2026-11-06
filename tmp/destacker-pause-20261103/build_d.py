"""最新C版から段番号の限定加算と共通Pauseの手動並列枝を反映する。"""
from pathlib import Path
from copy import deepcopy,copy
import zipfile,json,re,hashlib,io,sys,csv,time
sys.stdout.reconfigure(encoding='utf-8')
start=time.monotonic();b=Path(__file__).parent
info=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
src=Path(info['source']);raw=src.read_bytes()
assert hashlib.sha256(raw).hexdigest()==info['sha256'],'C版が外部更新されたため停止'
dest=src.with_name(src.name.replace('20261103C.smc2','20261103D.smc2'))
assert dest!=src and not dest.exists(),'D版が既にあるため停止'
changes=[];branch_changes=[];already=[]
def objects(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from objects(v)
 elif isinstance(x,list):
  for v in x:yield from objects(v)
def ids_ok(row):
 values=[v['Ix'] for e in row['CLs'] for v in objects(e) if 'Ix' in v]
 assert len(values)==len(set(values))
 assert not set(values)&({row['LRI'],row['RRI']}|{v['Ix'] for v in row.get('VLs',[])})
with zipfile.ZipFile(io.BytesIO(raw)) as zin:
 assert zin.testzip() is None
 parts={s:info['sections'][s] for s in ['Destacker_段バラシ','Output_出力']}
 originals={s:zin.read(p) for s,p in parts.items()}
 lines={s:data.decode('utf-8-sig').splitlines(keepends=True) for s,data in originals.items()}
 before={s:[json.loads(l) for l in ls] for s,ls in lines.items()};after=deepcopy(before)
 assert len(after['Destacker_段バラシ'])==21
 def shift(x,row,path):
  if isinstance(x,dict):
   v=x.get('Var');m=re.fullmatch(r'Destacker_M\[(\d+)\]',v) if isinstance(v,str) else None
   if row>=12 and m and int(m[1])>=15:
    new=f'Destacker_M[{int(m[1])+1}]'
    changes.append({'行':row,'命令':x.get('__type'),'要素':x.get('Ix'),'旧':v,'新':new,'path':path+['Var']});x['Var']=new
   for k,v in x.items():
    if k!='Var':shift(v,row,path+[k])
  elif isinstance(x,list):
   for i,v in enumerate(x):shift(v,row,path+[i])
 for i,row in enumerate(after['Destacker_段バラシ']):shift(row,i,[i])
 assert len(changes)==36
 ds=after['Destacker_段バラシ']
 stage=[int(re.fullmatch(r'Destacker_M\[(\d+)\]',e['Var'])[1]) for e in objects(ds) if e.get('__type')=='ST' and re.fullmatch(r'Destacker_M\[\d+\]',e.get('Var',''))]
 assert stage==list(range(1,26)),stage
 assert before['Destacker_段バラシ'][:12]==ds[:12]
 target=[p for p in info['pause'] if p['common']]
 assert len(target)==100 and len({p['row'] for p in target})==100
 for p in target:
  i=p['row'];row=after['Output_出力'][i];original=deepcopy(row)
  pause=next(e for e in row['CLs'] if e.get('__type')=='LD' and e.get('Ix')==p['ix'] and e.get('Var')==p['var'])
  assert pause.get('Not') is True and p['y']==0
  x=p['x'];existing=[e for e in row['CLs'] if e.get('__type')=='LD' and e.get('Var')=='ManualMode' and e.get('X',0)==x and e.get('Y',0)==1 and not e.get('Not',False)]
  if existing:
   assert len(existing)==1
   assert all(any(v.get('X',0)==side and v.get('Y',0)==0 for v in row.get('VLs',[])) for side in [x,x+1])
   already.append(i);continue
  assert not any(v.get('X',0) in [x,x+1] and v.get('Y',0)==0 for v in row.get('VLs',[]))
  maxid=max([row['LRI'],row['RRI']]+[v.get('Ix',0) for v in objects(row)])
  # 1行目の下へ1段挿入し、元の手動・保持・出力分岐をそのまま下へ送る。
  for e in row['CLs']:
   if e.get('Y',0)>=1:e['Y']+=1
  vls=[]
  for v in row.get('VLs',[]):
   w=deepcopy(v);y=v.get('Y',0)
   if y>=1:w['Y']=y+1
   vls.append(w)
   if y==0:
    extra=deepcopy(v);extra['Y']=1;vls.append(extra)
  manual={'__type':'LD','Ix':maxid+1,'Var':'ManualMode','X':x,'Y':1}
  row['CLs'].insert(row['CLs'].index(pause)+1,manual)
  vls.extend([{'Ix':maxid+2,'X':x},{'Ix':maxid+3,'X':x+1}]);row['VLs']=vls
  ids_ok(row)
  remaining=[deepcopy(e) for e in row['CLs'] if e is not manual]
  for e in remaining:
   if e.get('Y',0)>=2:e['Y']-=1
  assert remaining==original['CLs'],'既存命令の条件・変数が変化'
  assert {k:v for k,v in row.items() if k not in ['CLs','VLs']}=={k:v for k,v in original.items() if k not in ['CLs','VLs']}
  branch_changes.append({'行':i,'Pause':p['var'],'Pause要素':p['ix'],'X':x,'追加ManualMode要素':maxid+1,'左縦線要素':maxid+2,'右縦線要素':maxid+3,'出力コイル':p['coils']})
 assert len(branch_changes)==99 and already==[16]
 patches={};changed_rows={}
 for section,part in parts.items():
  out=[];changed_rows[section]=[]
  for i,(a,c,l) in enumerate(zip(before[section],after[section],lines[section])):
   if a==c:out.append(l)
   else:
    changed_rows[section].append(i)
    ending='\r\n' if l.endswith('\r\n') else '\n' if l.endswith('\n') else ''
    out.append(json.dumps(c,ensure_ascii=False,separators=(',',':'))+ending)
  patches[part]=(b'\xef\xbb\xbf' if originals[section].startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8')
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w') as zout:
  zout.comment=zin.comment
  for e in zin.infolist():zout.writestr(copy(e),patches.get(e.filename,zin.read(e.filename)))
 result=buf.getvalue()
 with zipfile.ZipFile(io.BytesIO(result)) as z:
  assert z.testzip() is None and z.namelist()==zin.namelist()
  changed=[n for n in zin.namelist() if zin.read(n)!=z.read(n)];assert set(changed)==set(parts.values())
  for s,p in parts.items():assert [json.loads(l) for l in z.read(p).decode('utf-8-sig').splitlines()]==after[s]
 assert src.read_bytes()==raw
 with dest.open('xb') as f:f.write(result)
 assert dest.read_bytes()==result
 report={'source':str(src),'output':str(dest),'source_sha256':info['sha256'],'output_sha256':hashlib.sha256(result).hexdigest(),'stage_changes':len(changes),'stage_coils':stage,'common_pause_total':len(target),'manual_added':len(branch_changes),'already_done_rows':already,'other_pause_preserved':sum(not p['common'] for p in info['pause']),'changed_rows':changed_rows,'changed_parts':changed,'preserved_parts':len(zin.namelist())-2,'ZIP_CRC':'正常','native_Sysmac_build':'未実施','seconds':round(time.monotonic()-start,3),'branches':branch_changes,'stages':changes}
 (b/'build_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 for filename,records in [('段番号変更一覧.csv',[{k:v for k,v in r.items() if k!='path'} for r in changes]),('ManualMode追加一覧.csv',branch_changes)]:
  with (b/filename).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
 print(json.dumps({k:v for k,v in report.items() if k not in ['branches','stages','changed_rows']},ensure_ascii=False))
