"""行分離の差分と同一スキャンでの実行条件を確認してD版を上書きする。"""
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from collections import defaultdict
import hashlib,json,itertools,re,os

b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
src=Path(m['source']);stage=Path(m['staged']);backup=Path(m['backup'])
assert backup.read_bytes()==src.read_bytes()
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
assert m['native_validation']['box_section']=='TOTAL=29 PARSE_FAIL=0 MODEL_FAIL=0'
assert m['native_validation']['row28_IST_input_edges']==1

def run_gate(row,env):
 edges=defaultdict(set)
 for v in row['VLs']:
  p=(v.get('X',0),v.get('Y',0));q=(p[0],p[1]+1)
  edges[p].add(q);edges[q].add(p)
 for c in row['CLs']:
  x,y=c.get('X',0),c.get('Y',0)
  if c['__type']=='HL' or (c['__type']=='LD' and bool(env[c['Var']])!=c.get('Not',False)):
   edges[(x,y)].add((x+1,y))
 height=max(c.get('Y',0) for c in row['CLs']);seen={(0,y) for y in range(height+1)};todo=list(seen)
 while todo:
  for n in edges[todo.pop()]-seen:seen.add(n);todo.append(n)
 return {c['__type']:(c.get('X',0),c.get('Y',0)) in seen for c in row['CLs'] if c['__type'] in ['ST','IST']}

with ZipFile(backup) as a,ZipFile(stage) as z:
 assert z.testzip() is None and a.namelist()==z.namelist()
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==[m['target']]
 oldlines=a.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 newlines=z.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 assert len(oldlines)==28 and len(newlines)==29 and newlines[:27]==oldlines[:27]
 old=json.loads(oldlines[27]);x=json.loads(newlines[27]);y=json.loads(newlines[28])
 oldst=next(c for c in old['CLs'] if c['__type']=='IST')['TXT']
 xst=next(c for c in x['CLs'] if c['__type']=='IST')['TXT']
 yst=next(c for c in y['CLs'] if c['__type']=='IST')['TXT']
 assert oldst==xst+'\r\n'+yst,'ST文字列は行分離以外変更しない'
 assert re.findall(r'(\w+)\s*:=',re.sub(r'//[^\n]*','',xst))==['RCON2_2_OUT_TargetPos_mm']*4
 assert re.findall(r'(\w+)\s*:=',re.sub(r'//[^\n]*','',yst))==['RCON2_3_OUT_TargetPos_mm']*4
 restore=deepcopy(x);next(c for c in restore['CLs'] if c['__type']=='IST')['TXT']=oldst
 restore['CMT']=old['CMT'];assert restore==old
 assert y['CLs'][0]=={'__type':'LD','Var':'BoxPacking_M[32]'}
 assert len(y['CLs'])==2 and y['VLs']==[]
 for values in itertools.product([False,True],repeat=4):
  env=dict(zip(['BoxPacking_M[31]','RCON2_4_MoveDone','BoxPacking_M[32]',''],values))
  oldrun=run_gate(old,env);newrun=run_gate(x,env)
  assert oldrun==newrun and oldrun['ST']==oldrun['IST']
  # 27行目の通常コイルはこのスキャンで更新され、28行目はその結果を見る。
  env['BoxPacking_M[32]']=newrun['ST']
  assert run_gate(y,env)['IST']==oldrun['IST']

data=stage.read_bytes();assert hashlib.sha256(data).hexdigest()==m['output_sha256']
temp=src.with_name(src.name+'.codex-yrow28-tmp');assert not temp.exists()
with temp.open('xb') as f:f.write(data)
assert temp.read_bytes()==data
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
os.replace(temp,src);assert src.read_bytes()==data
m['published']=True
m['independent_verification']={'other_parts_identical':209,'original_ST_text_preserved':True,'Y_calculation_occurrences':1,'X_row':27,'Y_row':28,'same_scan_gate_cases':16,'variable_tables_unchanged':True,'D_overwritten':True,'backup_verified':True}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(src),'verification':m['independent_verification'],'output_sha256':m['output_sha256']},ensure_ascii=False))
