from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
from collections import defaultdict
import json,re,io,hashlib
b=Path(__file__).parent
meta=json.loads((b.parent/'box-restore-ladder-20261105/verification.json').read_text(encoding='utf-8'))
p=Path(meta['output']);raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
assert sha==meta['output_sha256']
out=b.parents[1]/'outputs/box-order-F-20261105';out.mkdir(parents=True,exist_ok=True)
backup=out/(p.stem+'_番号整列前.smc2');assert not backup.exists()
mapping={4:{1:1,2:2,5:3,3:4,4:5},5:{1:1,4:2,2:3,5:4,6:5,3:6}}
changes=[]
with ZipFile(io.BytesIO(raw)) as z:
 patches={}
 for part in [meta['box_part'],meta['rcon_part']]:
  original=z.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True);new=[]
  for i,line in enumerate(lines):
   row=json.loads(line);before=deepcopy(row)
   def visit(v):
    if isinstance(v,dict):
     for k,x in v.items():
      if k=='Var' and isinstance(x,str):
       m=re.fullmatch(r'RCON2_([45])_Auto\[(\d+)\]',x)
       if m:
        axis,n=map(int,m.groups());nn=mapping[axis][n];v[k]=f'RCON2_{axis}_Auto[{nn}]'
        if n!=nn:changes.append([part,i,x,v[k]])
      else:visit(x)
    elif isinstance(v,list):
     for x in v:visit(x)
   visit(row)
   if part==meta['rcon_part'] and i in [401,441]:
    cs=[c for c in row['CLs'] if c['__type']=='LD' and re.fullmatch(r'RCON2_[45]_Auto\[\d+\]',c.get('Var',''))]
    for j,c in enumerate(sorted(cs,key=lambda c:c.get('Y',0))):c['Var']=f'RCON2_{4 if i==401 else 5}_Auto[{j+1}]'
   ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
   new.append(line if row==before else json.dumps(row,ensure_ascii=False,separators=(',',':'))+ending)
  data=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(new).encode('utf-8')
  if data!=original:patches[part]=data
 stream=io.BytesIO()
 with ZipFile(stream,'w') as w:
  w.comment=z.comment
  for info in z.infolist():w.writestr(copy(info),patches.get(info.filename,z.read(info.filename)))
 result=stream.getvalue()
 with ZipFile(io.BytesIO(result)) as w:
  assert w.testzip() is None
  assert [n for n in z.namelist() if z.read(n)!=w.read(n)]==[meta['box_part']]
  groups=defaultdict(list)
  for i,l in enumerate(w.read(meta['box_part']).decode('utf-8-sig').splitlines()):
   for c in json.loads(l)['CLs']:
    m=re.fullmatch(r'(RCON2_\d+_Auto)\[(\d+)\]',c.get('Var',''))
    if c['__type']=='ST' and m:groups[m[1]].append([i,int(m[2])])
  for values in groups.values():assert [n for _,n in values]==list(range(1,len(values)+1))
  assert w.read(meta['rcon_part'])==z.read(meta['rcon_part'])
 with backup.open('xb') as f:f.write(raw)
 stage=b/p.name;stage.write_bytes(result)
 report={'source':str(p),'staged':str(stage),'backup':str(backup),'source_sha256':sha,'output_sha256':hashlib.sha256(result).hexdigest(),'box_part':meta['box_part'],'groups':dict(groups),'changed_refs':len([x for x in changes if x[0]==meta['box_part']]),'other_parts_unchanged':211,'published':False}
 (b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
