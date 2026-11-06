"""独自制御を撤回。元Dの回路に要求/受け接点/参照修正だけを残す。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
import json,re,hashlib,io
b=Path(__file__).parent
previous=json.loads((b.parent/'box-improve-20261105/verification.json').read_text(encoding='utf-8'))
current=Path(previous['output']);baseline=Path(previous['archive'])
assert hashlib.sha256(current.read_bytes()).hexdigest()==previous['output_sha256']
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==previous['source_sha256']
dest=current.with_name(current.name.replace('20261105E.smc2','20261105F.smc2'));archive=current.parent/'履歴'/current.name;stage=b/dest.name
assert not dest.exists() and not archive.exists() and not stage.exists()
assert archive.parent.resolve().is_relative_to(current.parent.resolve())
partbox=previous['box_part'];partrcon=previous['rcon_part'];partout=previous['output_part']

def reindex(r):
 n=0
 for c in r['CLs']:
  if c['__type']!='HL':c['Ix']=n;n+=1
  for p in c.get('In',[])+c.get('Out',[]):
   if p['__type']=='PRM':p['Ix']=n;n+=1
 r['LRI']=n;r['RRI']=n+1;n+=2
 for v in r['VLs']:v['Ix']=n;n+=1

def encode(old,t):return (b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf-8')

with ZipFile(baseline) as d,ZipFile(current) as e:
 boxraw=d.read(partbox);boxlines=boxraw.decode('utf-8-sig').splitlines(keepends=True);box=[json.loads(l) for l in boxlines];assert len(box)==42
 for i,old,new in [(5,'RCON2_5_Auto[1]','RCON2_5_Auto[4]'),(11,'RCON2_5_Auto[2]','RCON2_5_Auto[5]'),(37,'RCON2_5_Auto[2]','RCON2_5_Auto[6]'),(38,'Out_CYw_Ejc_Cont_F_Auto[1]','Out_CYw_Ejc_Cont_F_Auto[2]'),(39,'Out_CYw_Ejc_Cont_H_Auto[1]','Out_CYw_Ejc_Cont_H_Auto[3]')]:
  candidates=[c for c in box[i]['CLs'] if c['__type']=='ST' and c.get('Var')==old];assert len(candidates)==1;candidates[0]['Var']=new
 assert box[11]['CLs'][0]['Var']=='BoxPacking_M[14]';box[11]['CLs'][0]['Var']='BoxPacking_M[16]'
 oldbox=[json.loads(l) for l in boxlines]
 def serialize_lines(raw,lines,old,new):
  result=[]
  for line,a,c in zip(lines,old,new):
   ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
   result.append(line if a==c else json.dumps(c,ensure_ascii=False,separators=(',',':'))+ending)
  return encode(raw,''.join(result))
 rconraw=d.read(partrcon);rconlines=rconraw.decode('utf-8-sig').splitlines(keepends=True);oldr=[json.loads(l) for l in rconlines];rcon=deepcopy(oldr);assert len(rcon)==449
 for i,axis,count in [(401,4,5),(441,5,6)]:
  row=rcon[i];extra=count-3
  assert [c['Var'] for c in row['CLs'] if c['__type']=='LD' and re.fullmatch(f'RCON2_{axis}_Auto\\[\\d+\\]',c.get('Var',''))]==[f'RCON2_{axis}_Auto[{j}]' for j in [1,2,3]]
  # 既存3つの要求の後ろ、自己保持枝より前へ、要求の並列枝だけを挿入する。
  for c in row['CLs']:
   if c.get('Y',0)>=3:c['Y']+=extra
  vls=[]
  for v in row['VLs']:
   y=v.get('Y',0)
   if y==2:
    for at in range(2,3+extra):nv=deepcopy(v);nv['Y']=at;vls.append(nv)
   elif y>=3:nv=deepcopy(v);nv['Y']+=extra;vls.append(nv)
   else:vls.append(deepcopy(v))
  row['VLs']=vls+[{'X':1,'Y':y} for y in range(2,count-1)]
  row['CLs'] += [{'__type':'LD','Var':f'RCON2_{axis}_Auto[{j}]','Y':j-1} for j in range(4,count+1)]
  row['CMT']=row.get('CMT','')+f'\r\n既存の開始条件/100ms確認/自己保持は保持し、自動要求[1]～[{count}]だけを並列に追加。'
  reindex(row)
 patches={partbox:serialize_lines(boxraw,boxlines,oldbox,box),partrcon:serialize_lines(rconraw,rconlines,oldr,rcon),partout:e.read(partout)}
 stream=io.BytesIO()
 with ZipFile(stream,'w') as f:
  f.comment=d.comment
  for info in d.infolist():f.writestr(copy(info),patches.get(info.filename,d.read(info.filename)))
 data=stream.getvalue()
 with ZipFile(io.BytesIO(data)) as f:
  assert f.testzip() is None and f.namelist()==d.namelist()
  changes=[n for n in d.namelist() if d.read(n)!=f.read(n)];assert set(changes)==set(patches)
 with stage.open('xb') as f:f.write(data)
 report={'source':str(current),'baseline':str(baseline),'output':str(dest),'archive':str(archive),'staged':str(stage),'source_sha256':previous['output_sha256'],'baseline_sha256':previous['source_sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),'box_part':partbox,'rcon_part':partrcon,'output_part':partout,'changes_from_D':changes,'unchanged_parts_from_D':len(d.namelist())-3,'native_validation':None,'independent_audit':None,'published':False,'archived':False}
 (b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
