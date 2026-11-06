"""画像の9行目以降に限ってDestacker_Mの11以上の添字を2加算する。"""
from pathlib import Path
from copy import deepcopy,copy
import zipfile,json,re,hashlib,io,sys,csv,time,collections
sys.stdout.reconfigure(encoding='utf-8')
start=time.monotonic()
base=Path(__file__).parent
info=json.loads((base/'inspection.json').read_text(encoding='utf-8'))
src=Path(info['source']);source=src.read_bytes()
assert hashlib.sha256(source).hexdigest()==info['sha256'],'原本の外部更新を検出'
dest=src.with_name(src.name.replace('20261103A.smc2','20261103B.smc2'))
assert dest!=src and not dest.exists(),'保存先は未使用のB版が必要'
part=info['target'];changes=[]
with zipfile.ZipFile(io.BytesIO(source)) as zin:
 assert zin.testzip() is None
 raw=zin.read(part);bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
 lines=raw.decode('utf-8-sig').splitlines(keepends=True)
 old=[json.loads(l) for l in lines];assert len(old)==19
 new=deepcopy(old)
 def shift(v,row,path):
  if isinstance(v,dict):
   var=v.get('Var');m=re.fullmatch(r'Destacker_M\[(\d+)\]',var) if isinstance(var,str) else None
   if row>=9 and m and int(m[1])>=11:
    value='Destacker_M['+str(int(m[1])+2)+']'
    changes.append({'表示行':row,'命令':v.get('__type'),'要素番号':v.get('Ix'),'旧':var,'新':value,'path':path+['Var']})
    v['Var']=value
   for k,x in v.items():
    if k!='Var':shift(x,row,path+[k])
  elif isinstance(v,list):
   for i,x in enumerate(v):shift(x,row,path+[i])
 for i,r in enumerate(new):shift(r,i,[i])
 assert len(changes)==32
 expect={tuple(c['path']):(c['旧'],c['新']) for c in changes};diff=[]
 def compare(a,b,path):
  assert type(a)==type(b)
  if isinstance(a,dict):
   assert list(a)==list(b)
   for k in a:compare(a[k],b[k],path+[k])
  elif isinstance(a,list):
   assert len(a)==len(b)
   for i in range(len(a)):compare(a[i],b[i],path+[i])
  elif a!=b:
   assert expect[tuple(path)]==(a,b);diff.append(tuple(path))
 compare(old,new,[]);assert set(diff)==set(expect)
 def coils(v):
  if isinstance(v,dict):
   if v.get('__type')=='ST' and re.fullmatch(r'Destacker_M\[\d+\]',v.get('Var','')):yield v['Var']
   for x in v.values():yield from coils(x)
  elif isinstance(v,list):
   for x in v:yield from coils(x)
 counter=collections.Counter(coils(new))
 duplicates={k:v for k,v in counter.items() if v>1}
 assert duplicates=={'Destacker_M[8]':2},duplicates
 assert set(coils(new[9:]))=={f'Destacker_M[{n}]' for n in range(13,24)}
 updated=[]
 for a,b,l in zip(old,new,lines):
  ending='\r\n' if l.endswith('\r\n') else '\n' if l.endswith('\n') else ''
  updated.append(l if a==b else json.dumps(b,ensure_ascii=False,separators=(',',':'))+ending)
 assert updated[:9]==lines[:9]
 patch=bom+''.join(updated).encode('utf-8')
 assert [json.loads(l) for l in patch.decode('utf-8-sig').splitlines()]==new
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w') as zout:
  zout.comment=zin.comment
  for e in zin.infolist():zout.writestr(copy(e),patch if e.filename==part else zin.read(e.filename))
 data=out.getvalue()
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert z.testzip() is None and z.namelist()==zin.namelist()
  changed=[n for n in z.namelist() if zin.read(n)!=z.read(n)];assert changed==[part]
 assert src.read_bytes()==source,'作業中に原本が更新されたため停止'
 with dest.open('xb') as f:f.write(data)
 assert dest.read_bytes()==data
 report={'source':str(src),'output':str(dest),'source_sha256':info['sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),'changed_entries':changed,'preserved_entry_count':len(zin.namelist())-1,'changed_variable_references':len(changes),'unchanged_rows':list(range(9)),'new_coil_range':[13,23],'preexisting_duplicate_coils':duplicates,'Sysmac全体再ビルド':'未実施','PLC接続と転送':'未実施','seconds':round(time.monotonic()-start,3),'changes':changes}
 (base/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 with (base/'変更一覧.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['表示行','命令','要素番号','旧','新']);w.writeheader();w.writerows({k:v for k,v in c.items() if k!='path'} for c in changes)
 print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False))
