"""段バラシセクション内の指定された段番号だけを変更し別名で保存する。"""
from pathlib import Path
from copy import deepcopy,copy
import argparse,zipfile,json,re,hashlib,io,sys,csv,time
sys.stdout.reconfigure(encoding='utf-8')
ap=argparse.ArgumentParser()
ap.add_argument('--mode',choices=['all','connections'],required=True)
args=ap.parse_args()
start=time.monotonic()
base=Path(__file__).parent
info=json.loads((base/'inspection.json').read_text(encoding='utf-8'))
src=Path(info['source'])
source=src.read_bytes()
assert hashlib.sha256(source).hexdigest()==info['sha256'],'原本が更新されたため停止'
dest=src.with_name(src.name.replace('20261102A.smc2','20261102B.smc2'))
assert dest!=src and not dest.exists(),'出力先は新規の別名が必要'
part='a171e655-68f3-4650-8b9f-6d33ff2eccf1/fb95842e-fdb2-46b7-9a81-473d52d66cbf.xml'
changes=[]
with zipfile.ZipFile(io.BytesIO(source)) as zin:
 assert zin.testzip() is None
 raw=zin.read(part)
 bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
 lines=raw.decode('utf-8-sig').splitlines(keepends=True)
 old=[json.loads(l) for l in lines]
 assert len(old)==17
 new=deepcopy(old)
 def edit(x,row,path):
  if isinstance(x,dict):
   var=x.get('Var')
   if isinstance(var,str):
    m=re.fullmatch(r'Destacker_M\[(\d+)\]',var)
    if m and row>=7 and int(m[1])>=7:
     # 7行目の前段入力2点は、参照先が0～6行目にあるため接続維持モードでは保持する。
     keep=args.mode=='connections' and row==7 and x.get('__type')=='LD' and x.get('Ix') in [2,9]
     if not keep:
      value=f'Destacker_M[{int(m[1])+4}]'
      changes.append({'表示行':row,'命令':x.get('__type'),'要素番号':x.get('Ix'),'旧':var,'新':value,'path':path+['Var']})
      x['Var']=value
   for k,v in x.items():
    if k!='Var':edit(v,row,path+[k])
  elif isinstance(x,list):
   for i,v in enumerate(x):edit(v,row,path+[i])
 for row,r in enumerate(new):edit(r,row,[row])
 assert changes
 expected={tuple(c['path']):(c['旧'],c['新']) for c in changes}
 diffs=[]
 def compare(a,b,path):
  assert type(a)==type(b)
  if isinstance(a,dict):
   assert list(a)==list(b)
   for k in a:compare(a[k],b[k],path+[k])
  elif isinstance(a,list):
   assert len(a)==len(b)
   for i in range(len(a)):compare(a[i],b[i],path+[i])
  elif a!=b:
   assert tuple(path) in expected and expected[tuple(path)]==(a,b)
   diffs.append(tuple(path))
 compare(old,new,[])
 assert set(diffs)==set(expected)
 updated=[]
 for i,(a,b,l) in enumerate(zip(old,new,lines)):
  if a==b:updated.append(l)
  else:
   ending='\r\n' if l.endswith('\r\n') else '\n' if l.endswith('\n') else ''
   updated.append(json.dumps(b,ensure_ascii=False,separators=(',',':'))+ending)
 assert updated[:7]==lines[:7]
 patch=bom+''.join(updated).encode('utf-8')
 rebuilt=[json.loads(l) for l in patch.decode('utf-8-sig').splitlines()]
 assert rebuilt==new
 coils=[]
 def collect(v):
  if isinstance(v,dict):
   if v.get('__type')=='ST' and re.fullmatch(r'Destacker_M\[\d+\]',v.get('Var','')):coils.append(v['Var'])
   for x in v.values():collect(x)
  elif isinstance(v,list):
   for x in v:collect(x)
 collect(rebuilt)
 assert len(coils)==len(set(coils))==21
 assert set(coils)=={f'Destacker_M[{i}]' for i in range(1,22)}
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w') as zout:
  zout.comment=zin.comment
  for e in zin.infolist():zout.writestr(copy(e),patch if e.filename==part else zin.read(e.filename))
 candidate=out.getvalue()
 with zipfile.ZipFile(io.BytesIO(candidate)) as z:
  assert z.testzip() is None
  assert z.namelist()==zin.namelist()
  changed=[n for n in zin.namelist() if z.read(n)!=zin.read(n)]
  assert changed==[part]
  assert [json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines()]==new
 assert src.read_bytes()==source,'作業中の原本更新を検出'
 with dest.open('xb') as f:f.write(candidate)
 assert dest.read_bytes()==candidate
 report={'source':str(src),'output':str(dest),'mode':args.mode,'source_sha256':info['sha256'],'output_sha256':hashlib.sha256(candidate).hexdigest(),'changed_entries':changed,'preserved_entry_count':len(zin.namelist())-1,'changed_variable_references':len(changes),'unchanged_rows_0_to_6':True,'unique_coils':len(coils),'coil_indices':[1,21],'source_unchanged':True,'ZIP_CRC':'正常','Sysmac読込と全体再ビルド':'未実施','実機接続と転送':'未実施','seconds':round(time.monotonic()-start,3),'changes':changes}
 (base/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 with (base/'変更一覧.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['表示行','命令','要素番号','旧','新']);w.writeheader();w.writerows({k:v for k,v in c.items() if k!='path'} for c in changes)
 print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False))
