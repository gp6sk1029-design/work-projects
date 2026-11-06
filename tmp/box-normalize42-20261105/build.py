"""工程を増やさず、43～49を42～48へ詰め、末尾工程49を保持する。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
from collections import Counter
import hashlib,json,re,io

b=Path(__file__).parent
m=json.loads((b.parent/'box-gap42-20261105/inspection.json').read_text(encoding='utf-8'))
src=Path(m['source']);raw=src.read_bytes();assert hashlib.sha256(raw).hexdigest()==m['sha256']
dest=src.with_name(src.name.replace('20261105C.smc2','20261105D.smc2'))
archive=src.parent/'履歴'/src.name;stage=b/dest.name
assert dest!=src and not dest.exists() and not archive.exists() and not stage.exists()
assert archive.parent.resolve().is_relative_to(src.parent.resolve()),'履歴が指定フォルダ外'
part=m['target']['part'];changes=[]
with ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 original=z.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 rows=[json.loads(l) for l in lines];assert len(rows)==42
 def coil_numbers(rr):return [int(re.fullmatch(r'BoxPacking_M\[(\d+)\]',c['Var'])[1]) for r in rr for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',c.get('Var',''))]
 assert coil_numbers(rows)==list(range(1,42))+list(range(43,50))+[49]
 terminal=[(len(rows)-1,i) for i,c in enumerate(rows[-1]['CLs']) if c['__type']=='ST' and c.get('Var')=='BoxPacking_M[49]'];assert len(terminal)==1
 terminal_path=[terminal[0][0],'CLs',terminal[0][1],'Var']
 new=deepcopy(rows)
 def visit(v,row,path):
  if isinstance(v,dict):
   for k,value in v.items():
    if k=='Var' and isinstance(value,str):
     match=re.fullmatch(r'BoxPacking_M\[(\d+)\]',value)
     if match and 43<=int(match[1])<=49 and path+[k]!=terminal_path:
      v[k]=f'BoxPacking_M[{int(match[1])-1}]';changes.append({'row':row,'path':path+[k],'old':value,'new':v[k]})
    elif k in ['TXT','CMT'] and isinstance(value,str):
     assert not any(int(n)>=42 for n in re.findall(r'BoxPacking_M\[(\d+)\]',value)),'ST/コメントに対象番号参照あり'
    else:visit(value,row,path+[k])
  elif isinstance(v,list):
   for i,value in enumerate(v):visit(value,row,path+[i])
 for i,r in enumerate(new):visit(r,i,[i])
 assert coil_numbers(new)==list(range(1,50))
 assert new[-1]['CLs'][0]['Var']=='BoxPacking_M[48]'
 assert new[-1]['CLs'][terminal[0][1]]['Var']=='BoxPacking_M[49]'
 assert new[35]==rows[35] and new[35]['CLs'][4]['Var']=='BoxPacking_M[42]'
 for d in m['declarations']:assert not any(int(n)>=42 for n in re.findall(r'EK="\[(\d+)\]"',d['line']))
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
 report={'source':str(src),'output':str(dest),'archive':str(archive),'staged':str(stage),'source_sha256':m['sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),'target':part,'row_count':42,'new_stages':0,'terminal_coil_preserved':terminal_path,'mapping':{str(n):n-1 for n in range(43,50)},'changed_refs':len(changes),'changes':changes,'coil_range_after':[1,49],'changed_parts':parts,'preserved_parts':len(z.namelist())-1,'native_validation':None,'published':False,'archived':False,'full_Sysmac_build':'未実施'}
 (b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False))
