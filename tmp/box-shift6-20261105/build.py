"""先頭判定[1]～[6]を保持し、2行目以降の工程[6]～[47]を1加算する。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
from collections import Counter
import hashlib,json,re,io

b=Path(__file__).parent
meta=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
src=Path(meta['source']);raw=src.read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['sha256']
dest=src.parent/'Codex編集用'/src.name.replace('20261105A.smc2','20261105B.smc2')
assert dest!=src and dest.parent.is_dir() and not dest.exists(),'既存ファイルを上書きしない'
stage=b/dest.name;assert not stage.exists()
part=meta['target']['part'];changes=[]
with ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 original=z.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 rows=[json.loads(l) for l in lines];assert len(rows)==41
 # 添字は正規表現で読み、文字列の固定切り出しへ依存しない。
 def coil_numbers(rr):return [int(re.fullmatch(r'BoxPacking_M\[(\d+)\]',c['Var'])[1]) for r in rr for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',c.get('Var',''))]
 beforecoils=Counter(coil_numbers(rows));assert beforecoils==Counter({**{i:1 for i in range(1,48)},6:2})
 updated=deepcopy(rows)
 def visit(v,row,path):
  if isinstance(v,dict):
   for k,value in v.items():
    if k=='Var' and isinstance(value,str):
     m=re.fullmatch(r'BoxPacking_M\[(\d+)\]',value)
     if m and int(m[1])>=6:
      v[k]=f'BoxPacking_M[{int(m[1])+1}]';changes.append({'row':row,'path':path+[k],'old':value,'new':v[k]})
    elif k in ['TXT','CMT'] and isinstance(value,str):
     assert not re.search(r'BoxPacking_M\[(\d+)\]',value),'STまたはコメントに個別番号参照があるため追加確認が必要'
    else:visit(value,row,path+[k])
  elif isinstance(v,list):
   for i,value in enumerate(v):visit(value,row,path+[i])
 for i in range(2,len(updated)):visit(updated[i],i,[i])
 assert updated[:2]==rows[:2]
 aftercoils=coil_numbers(updated);assert aftercoils==list(range(1,49)),aftercoils
 assert max(aftercoils)<=99 and len(set(aftercoils))==48
 assert len(changes)>100
 newlines=[]
 for old,new,line in zip(rows,updated,lines):
  ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
  newlines.append(line if old==new else json.dumps(new,ensure_ascii=False,separators=(',',':'))+ending)
 patched=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(newlines).encode('utf-8')
 stream=io.BytesIO()
 with ZipFile(stream,'w') as w:
  w.comment=z.comment
  for info in z.infolist():w.writestr(copy(info),patched if info.filename==part else z.read(info.filename))
 data=stream.getvalue()
 with ZipFile(io.BytesIO(data)) as w:
  assert w.testzip() is None and w.namelist()==z.namelist()
  changed=[n for n in z.namelist() if z.read(n)!=w.read(n)];assert changed==[part]
 assert src.read_bytes()==raw
 with stage.open('xb') as f:f.write(data)
 report={'source':str(src),'output':str(dest),'staged':str(stage),'source_sha256':meta['sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),'target':part,'row_count':41,'unchanged_rows':[0,1],'shifted_rows':[2,40],'old_shifted_range':[6,47],'new_shifted_range':[7,48],'coil_range_after':[1,48],'duplicate_coils_after':0,'changed_refs':len(changes),'changes':changes,'changed_parts':changed,'preserved_parts':len(z.namelist())-1,'native_validation':None,'published':False,'full_Sysmac_build':'未実施'}
 (b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False))
