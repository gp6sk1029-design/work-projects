"""段番号を1～24へ整理し、二つの旧8番を行と役割で区別する。"""
from pathlib import Path
from copy import deepcopy,copy
import zipfile,json,re,hashlib,io,sys,csv,time
sys.stdout.reconfigure(encoding='utf-8')
start=time.monotonic();base=Path(__file__).parent
info=json.loads((base/'B版番号確認.json').read_text(encoding='utf-8'))
src=Path(info['file']);source=src.read_bytes()
assert hashlib.sha256(source).hexdigest()==info['sha256'],'B版が外部更新されたため停止'
assert info['coil_order']==[1,2,3,4,5,7,8,8]+list(range(10,26))
dest=src.with_name(src.name.replace('20261103B.smc2','20261103C.smc2'))
assert dest!=src and not dest.exists(),'C版の保存先が使用済み'
part=info['target'];changes=[]
with zipfile.ZipFile(io.BytesIO(source)) as zin:
 raw=zin.read(part);bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
 lines=raw.decode('utf-8-sig').splitlines(keepends=True)
 old=[json.loads(l) for l in lines];assert len(old)==21
 new=deepcopy(old)
 def edit(v,row,path):
  if isinstance(v,dict):
   var=v.get('Var');m=re.fullmatch(r'Destacker_M\[(\d+)\]',var) if isinstance(var,str) else None
   if m:
    n=int(m[1]);out=n
    if n==7:out=6
    elif n==8:
     if row==4:out=7
     elif row==5:
      # 4行目を読む先頭接点と5行目自身の自己保持/コイルを分ける。
      assert (v.get('__type'),v.get('Ix'),v.get('Y',0)) in [('LD',None,0),('LD',3,1),('ST',4,0)]
      out=7 if v.get('__type')=='LD' and v.get('Y',0)==0 else 8
     else:raise AssertionError('想定外の旧8番参照')
    elif n==9:out=8
    elif n>=10:out=n-1
    if out!=n:
     value=f'Destacker_M[{out}]'
     changes.append({'表示行':row,'命令':v.get('__type'),'要素番号':v.get('Ix'),'旧':var,'新':value,'path':path+['Var']})
     v['Var']=value
   for k,x in v.items():
    if k!='Var':edit(x,row,path+[k])
  elif isinstance(v,list):
   for i,x in enumerate(v):edit(x,row,path+[i])
 for i,v in enumerate(new):edit(v,i,[i])
 expected={tuple(x['path']):(x['旧'],x['新']) for x in changes};actual=[]
 def check(a,b,path):
  assert type(a)==type(b)
  if isinstance(a,dict):
   assert list(a)==list(b)
   for k in a:check(a[k],b[k],path+[k])
  elif isinstance(a,list):
   assert len(a)==len(b)
   for i in range(len(a)):check(a[i],b[i],path+[i])
  elif a!=b:assert expected[tuple(path)]==(a,b);actual.append(tuple(path))
 check(old,new,[]);assert set(actual)==set(expected)
 def elements(v):
  if isinstance(v,dict):
   if 'Var' in v:yield v
   for x in v.values():yield from elements(x)
  elif isinstance(v,list):
   for x in v:yield from elements(x)
 coilnums=[int(re.fullmatch(r'Destacker_M\[(\d+)\]',x['Var'])[1]) for x in elements(new) if x.get('__type')=='ST' and re.fullmatch(r'Destacker_M\[\d+\]',x['Var'])]
 assert coilnums==list(range(1,25)),coilnums
 refs=[int(re.fullmatch(r'Destacker_M\[(\d+)\]',x['Var'])[1]) for x in elements(new) if re.fullmatch(r'Destacker_M\[\d+\]',x['Var'])]
 assert set(refs)==set(coilnums)
 other=lambda rows:[x for x in elements(rows) if not x['Var'].startswith('Destacker_M[')]
 assert other(old)==other(new),'外向き指令を含む他の変数変更を検出'
 updated=[]
 for a,b,l in zip(old,new,lines):
  ending='\r\n' if l.endswith('\r\n') else '\n' if l.endswith('\n') else ''
  updated.append(l if a==b else json.dumps(b,ensure_ascii=False,separators=(',',':'))+ending)
 patch=bom+''.join(updated).encode('utf-8')
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w') as zout:
  zout.comment=zin.comment
  for e in zin.infolist():zout.writestr(copy(e),patch if e.filename==part else zin.read(e.filename))
 data=out.getvalue()
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert z.testzip() is None and z.namelist()==zin.namelist()
  assert [n for n in zin.namelist() if zin.read(n)!=z.read(n)]==[part]
  assert [json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines()]==new
 assert src.read_bytes()==source
 with dest.open('xb') as f:f.write(data)
 assert dest.read_bytes()==data
 result={'source':str(src),'output':str(dest),'source_sha256':info['sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),'target':part,'changed_references':len(changes),'coil_order':coilnums,'missing_coils':[],'duplicate_coils':[],'contacts_without_coils':[],'preserved_parts':len(zin.namelist())-1,'external_command_variables_unchanged':True,'ZIP_CRC':'正常','Sysmac全体再ビルド':'未実施','PLC接続と転送':'未実施','seconds':round(time.monotonic()-start,3),'changes':changes}
 (base/'C版修正検証.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 with (base/'C版変更一覧.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['表示行','命令','要素番号','旧','新']);w.writeheader();w.writerows({k:v for k,v in c.items() if k!='path'} for c in changes)
 print(json.dumps({k:v for k,v in result.items() if k!='changes'},ensure_ascii=False))
