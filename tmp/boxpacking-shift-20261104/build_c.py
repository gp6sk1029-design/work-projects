"""10行目以降のBoxPacking_M添字14以上を一度で1加算する。"""
from pathlib import Path
from copy import deepcopy,copy
import zipfile,json,re,hashlib,io,sys,csv,time
sys.stdout.reconfigure(encoding='utf-8')
started=time.monotonic();b=Path(__file__).parent
info=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
src=Path(info['source']);raw=src.read_bytes()
assert hashlib.sha256(raw).hexdigest()==info['sha256'],'元B版が外部更新されたため停止'
dest=src.with_name(src.name.replace('20261104B.smc2','20261104C.smc2'))
assert dest!=src and not dest.exists(),'C版の保存先が使用済み'
changes=[]
with zipfile.ZipFile(io.BytesIO(raw)) as zin:
 assert zin.testzip() is None
 original=zin.read(info['target']);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 old=[json.loads(l) for l in lines];assert len(old)==28
 new=deepcopy(old)
 def shift(x,row,path):
  if isinstance(x,dict):
   var=x.get('Var');m=re.fullmatch(r'BoxPacking_M\[(\d+)\]',var) if isinstance(var,str) else None
   if row>=10 and m and int(m[1])>=14:
    value=f'BoxPacking_M[{int(m[1])+1}]'
    changes.append({'表示行':row,'命令':x.get('__type'),'要素番号':x.get('Ix'),'旧':var,'新':value,'path':path+['Var']});x['Var']=value
   for k,v in x.items():
    if k!='Var':shift(v,row,path+[k])
  elif isinstance(x,list):
   for i,v in enumerate(x):shift(v,row,path+[i])
 for i,r in enumerate(new):shift(r,i,[i])
 assert len(changes)==58
 def walk(x):
  if isinstance(x,dict):
   yield x
   for v in x.values():yield from walk(v)
  elif isinstance(x,list):
   for v in x:yield from walk(v)
 coils=[int(re.fullmatch(r'BoxPacking_M\[(\d+)\]',e['Var'])[1]) for e in walk(new) if e.get('__type')=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',e.get('Var',''))]
 assert coils==list(range(1,33)),coils
 allowed={tuple(r['path']):(r['旧'],r['新']) for r in changes};checked=[]
 def compare(a,c,path):
  assert type(a)==type(c)
  if isinstance(a,dict):
   assert list(a)==list(c)
   for k in a:compare(a[k],c[k],path+[k])
  elif isinstance(a,list):
   assert len(a)==len(c)
   for i in range(len(a)):compare(a[i],c[i],path+[i])
  elif a!=c:assert allowed[tuple(path)]==(a,c);checked.append(tuple(path))
 compare(old,new,[]);assert set(allowed)==set(checked)
 assert old[:10]==new[:10]
 output=[]
 for a,c,line in zip(old,new,lines):
  ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
  output.append(line if a==c else json.dumps(c,ensure_ascii=False,separators=(',',':'))+ending)
 patch=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(output).encode('utf-8')
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w') as zout:
  zout.comment=zin.comment
  for e in zin.infolist():zout.writestr(copy(e),patch if e.filename==info['target'] else zin.read(e.filename))
 result=buf.getvalue()
 with zipfile.ZipFile(io.BytesIO(result)) as z:
  assert z.testzip() is None and z.namelist()==zin.namelist()
  assert [n for n in zin.namelist() if zin.read(n)!=z.read(n)]==[info['target']]
  assert [json.loads(l) for l in z.read(info['target']).decode('utf-8-sig').splitlines()]==new
 assert src.read_bytes()==raw
 with dest.open('xb') as f:f.write(result)
 assert dest.read_bytes()==result
 report={'source':str(src),'output':str(dest),'source_sha256':info['sha256'],'output_sha256':hashlib.sha256(result).hexdigest(),'target':info['target'],'changed_references':len(changes),'coil_order':coils,'unchanged_rows':list(range(10)),'preserved_parts':len(zin.namelist())-1,'ZIP_CRC':'正常','SysmacStudio全体再ビルド':'未実施','PLC接続と転送':'未実施','seconds':round(time.monotonic()-started,3),'changes':changes}
 (b/'build_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 with (b/'変更一覧.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['表示行','命令','要素番号','旧','新']);w.writeheader();w.writerows({k:v for k,v in x.items() if k!='path'} for x in changes)
 print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False))
