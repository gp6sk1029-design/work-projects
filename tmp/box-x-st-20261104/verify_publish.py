"""生成済みZIPを独立に読み直し、差分・条件・ST座標式を検査して公開する。"""
from pathlib import Path
from zipfile import ZipFile
from collections import defaultdict
from copy import deepcopy
import json,re,hashlib,itertools

base=Path(__file__).parent
meta=json.loads((base/'verification.json').read_text(encoding='utf-8'))
src=Path(meta['source']);stage=Path(meta['staged']);dst=Path(meta['output'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==meta['source_sha256']
assert hashlib.sha256(stage.read_bytes()).hexdigest()==meta['output_sha256']
assert meta['native_validation']['application_build_verified'] is False
native_nodes=meta['native_validation']['row27_nodes']
assert [n['input_edges'] for n in native_nodes if n['type']=='InlineStructuredTextModel']==[1]

def enabled(row,env):
 edges=defaultdict(set)
 for v in row['VLs']:
  a=(v.get('X',0),v.get('Y',0));b=(a[0],a[1]+1)
  edges[a].add(b);edges[b].add(a)
 for c in row['CLs']:
  x,y=c.get('X',0),c.get('Y',0)
  if c['__type']=='HL' or (c['__type']=='LD' and bool(env[c['Var']])!=c.get('Not',False)):
   edges[(x,y)].add((x+1,y))
 seen={(0,0),(0,1)};todo=list(seen)
 while todo:
  for n in edges[todo.pop()]-seen:seen.add(n);todo.append(n)
 return {c['__type']:(c.get('X',0),c.get('Y',0)) in seen for c in row['CLs'] if c['__type'] in ['ST','IST']}

with ZipFile(src) as a,ZipFile(stage) as z:
 assert z.testzip() is None and a.namelist()==z.namelist() and len(z.namelist())==210
 changes=[n for n in a.namelist() if a.read(n)!=z.read(n)]
 assert changes==meta['changed_parts'] and len(changes)==2
 part=meta['target'];oldlines=a.read(part).decode('utf-8-sig').splitlines(keepends=True);lines=z.read(part).decode('utf-8-sig').splitlines(keepends=True)
 assert len(lines)==len(oldlines)==28 and lines[:27]==oldlines[:27]
 before=json.loads(oldlines[27]);after=json.loads(lines[27]);restored=deepcopy(after)
 ist=restored['CLs'].pop();assert ist['__type']=='IST' and ist['X']==3 and ist['Y']==1
 assert restored['VLs'].pop()=={'Ix':9,'X':3};del restored['CMT'];assert restored==before
 for flags in itertools.product([False,True],repeat=4):
  env=dict(zip(['BoxPacking_M[31]','RCON2_4_MoveDone','BoxPacking_M[32]',''],flags))
  previous=enabled(before,env)['ST'];current=enabled(after,env)
  assert current['ST']==current['IST']==previous
 st=ist['TXT'];assert st.encode('utf-8')==Path(meta['ST']).read_bytes().removeprefix(b'\xef\xbb\xbf')
 # プログラム中の代入先はX軸目標のみに限定される。
 executable=re.sub(r'//[^\n]*','',st)
 assert re.findall(r'(\w+)\s*:=',executable)==['RCON2_2_OUT_TargetPos_mm']*4
 blocks=re.findall(r'(?:IF|ELSIF)\s+((?:\(Box_Total_CT = INT#\d+\)\s*(?:OR\s*)?)+)THEN\s+RCON2_2_OUT_TargetPos_mm\s*:=\s*(.*?);',executable,re.S)
 assert len(blocks)==4 and executable.count('END_IF;')==1
 all_counts=[int(x) for cond,_ in blocks for x in re.findall(r'INT#(\d+)',cond)]
 assert sorted(all_counts)==list(range(5,81,5)) and len(set(all_counts))==16
 tested=0
 for start,pitch in [(123.5,12.5),(123.5,-12.5),(123.5,0.)]:
  for number,count in enumerate(range(5,81,5)):
   matches=[expr for cond,expr in blocks if count in map(int,re.findall(r'INT#(\d+)',cond))]
   assert len(matches)==1
   expr=matches[0].replace('HMI_RCON2_2_OUT_TargetPos[3]',repr(start)).replace('HMI_RCON2_2_OUT_TargetPos[4]',f'({pitch})').replace('LREAL#','')
   assert re.fullmatch(r'[\d\s.()+*\-]+',expr)
   result=eval('('+expr+')',{'__builtins__':{}},{})
   assert result==start+(number%4)*pitch;tested+=1
 invalid=[-5,0,1,4,6,79,81,85]
 assert all(not any(c in map(int,re.findall(r'INT#(\d+)',cond)) for cond,_ in blocks) for c in invalid)
 localpart=changes[1];oldlocal=a.read(localpart).decode('utf-8-sig');newlocal=z.read(localpart).decode('utf-8-sig')
 olddefs=oldlocal.splitlines();newdefs=newlocal.splitlines();assert len(olddefs)==len(newdefs)
 changeddefs=[(u,v) for u,v in zip(olddefs,newdefs) if u!=v];assert len(changeddefs)==1
 assert '\tN=HMI_RCON2_2_OUT_TargetPos\t' in changeddefs[0][0]
 assert all(re.sub(r'\tEC=.*','',u)==re.sub(r'\tEC=.*','',v) for u,v in changeddefs)
 declarations={}
 for line in newdefs:
  if line.startswith('++D='):
   fields=dict(t.split('=',1) for t in line[2:].split('\t') if '=' in t);declarations[fields['N']]=fields
 assert declarations['Box_Total_CT']['D']=='INT'
 assert declarations['RCON2_2_OUT_TargetPos_mm']['D']=='LREAL'
 assert declarations['HMI_RCON2_2_OUT_TargetPos']['D']=='ARRAY[0..99] OF LREAL'
 assert src.read_bytes() and hashlib.sha256(src.read_bytes()).hexdigest()==meta['source_sha256']

meta['independent_verification']={'coordinate_cases':tested,'counter_positions':16,'invalid_count_cases':8,'gate_truth_table_cases':16,'other_parts_identical':208,'row_0_through_26_byte_identical':True,'counter_rows_13_14_unchanged':True,'Y_Z_unchanged':True,'original_unchanged':True}
if not dst.exists():
 with dst.open('xb') as f:f.write(stage.read_bytes())
assert dst.read_bytes()==stage.read_bytes()
meta['published']=True
(base/'verification.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(dst),'verification':meta['independent_verification'],'native_model':'読込み・接続エラー0','Sysmac_build':'未実施'},ensure_ascii=False))
