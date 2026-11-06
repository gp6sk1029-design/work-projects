"""10行目の後側[15]から繰下げ、前工程[15]接点を保持してC版を作る。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
from collections import Counter
import hashlib,json,re,io

b=Path(__file__).parent;m=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
src=Path(m['source']);raw=src.read_bytes();assert hashlib.sha256(raw).hexdigest()==m['sha256']
dest=src.with_name(src.name.replace('20261105B.smc2','20261105C.smc2'))
history=src.parent/'履歴';archive=history/src.name
assert dest!=src and not dest.exists() and not archive.exists()
assert history.resolve().is_relative_to(src.parent.resolve()),'履歴が指定フォルダの外にある'
stage=b/dest.name;assert not stage.exists()
part=m['target']['part'];changes=[]
with ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 original=z.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 rows=[json.loads(l) for l in lines];assert len(rows)==42
 def coils(rr):return [int(re.fullmatch(r'BoxPacking_M\[(\d+)\]',c['Var'])[1]) for r in rr for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',c.get('Var',''))]
 assert Counter(coils(rows))==Counter({**{i:1 for i in range(1,49)},15:2})
 assert rows[10]['CLs'][0]=={'__type':'LD','Var':'BoxPacking_M[15]'}
 assert [c['Var'] for c in rows[9]['CLs'] if c['__type']=='ST' and c.get('Var','').startswith('BoxPacking_M[')]==['BoxPacking_M[15]']
 new=deepcopy(rows)
 boundary=[10,'CLs',0,'Var']
 def visit(v,row,path):
  if isinstance(v,dict):
   for k,value in v.items():
    if k=='Var' and isinstance(value,str):
     match=re.fullmatch(r'BoxPacking_M\[(\d+)\]',value)
     if match and int(match[1])>=15 and path+[k]!=boundary:
      v[k]=f'BoxPacking_M[{int(match[1])+1}]';changes.append({'row':row,'path':path+[k],'old':value,'new':v[k]})
    elif k in ['TXT','CMT'] and isinstance(value,str):
     assert not re.search(r'BoxPacking_M\[\d+\]',value),'ST/コメントに番号参照あり、個別確認が必要'
    else:visit(value,row,path+[k])
  elif isinstance(v,list):
   for i,value in enumerate(v):visit(value,row,path+[i])
 for i in range(10,len(new)):visit(new[i],i,[i])
 assert new[:10]==rows[:10] and new[10]['CLs'][0]==rows[10]['CLs'][0]
 assert coils(new)==list(range(1,50)),coils(new)
 assert max(coils(new))<=99
 # 配列要素コメントに繰下げ対象の説明が存在しないことも確認する。
 for d in m['declarations']:
  assert not any(int(i)>=15 for i in re.findall(r'EK="\[(\d+)\]"',d['line']))
 newlines=[]
 for old,r,line in zip(rows,new,lines):
  ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
  newlines.append(line if old==r else json.dumps(r,ensure_ascii=False,separators=(',',':'))+ending)
 patched=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(newlines).encode('utf-8')
 stream=io.BytesIO()
 with ZipFile(stream,'w') as w:
  w.comment=z.comment
  for info in z.infolist():w.writestr(copy(info),patched if info.filename==part else z.read(info.filename))
 data=stream.getvalue()
 with ZipFile(io.BytesIO(data)) as w:
  assert w.testzip() is None and w.namelist()==z.namelist()
  parts=[n for n in z.namelist() if z.read(n)!=w.read(n)];assert parts==[part]
 assert src.read_bytes()==raw
 with stage.open('xb') as f:f.write(data)
 report={'source':str(src),'output':str(dest),'archive':str(archive),'staged':str(stage),'source_sha256':m['sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),'target':part,'row_count':42,'unchanged_rows':[0,9],'preserved_predecessor_contact':boundary,'changed_refs':len(changes),'changes':changes,'coil_range_after':[1,49],'changed_parts':parts,'preserved_parts':len(z.namelist())-1,'native_validation':None,'published':False,'archived':False,'full_Sysmac_build':'未実施'}
 (b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False))
