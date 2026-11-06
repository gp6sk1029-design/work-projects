"""保存後の段番号・既存命令保持・全100分岐と局所導通を独立検証する。"""
from pathlib import Path
from copy import deepcopy
import zipfile,json,re,hashlib,sys,collections,itertools
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
meta=json.loads((b/'build_verification.json').read_text(encoding='utf-8'))
info=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
src=Path(meta['source']);dst=Path(meta['output']);stagechanges=0
def compare_stage(a,c,path):
 global stagechanges
 assert type(a)==type(c)
 if isinstance(a,dict):
  assert list(a)==list(c)
  for k in a:compare_stage(a[k],c[k],path+[k])
 elif isinstance(a,list):
  assert len(a)==len(c)
  for i in range(len(a)):compare_stage(a[i],c[i],path+[i])
 else:
  expected=a
  if path[-1]=='Var' and path[0]>=12 and isinstance(a,str):
   m=re.fullmatch(r'Destacker_M\[(\d+)\]',a)
   if m and int(m[1])>=15:expected=f'Destacker_M[{int(m[1])+1}]';stagechanges+=1
  assert c==expected,(path,a,c,expected)
def objects(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from objects(v)
 elif isinstance(x,list):
  for v in x:yield from objects(v)
def reachable(row,paused,manual,emergency,common_ix,override):
 edges=collections.defaultdict(set)
 def edge(a,c,bidirectional=False):
  edges[a].add(c)
  if bidirectional:edges[c].add(a)
 for e in row.get('VLs',[]):
  x=e.get('X',0);y=e.get('Y',0);edge((x,y),(x,y+1),True)
 for e in row['CLs']:
  kind=e['__type'];x=e.get('X',0);y=e.get('Y',0)
  assert kind in ['LD','HL','F','ST'],kind
  if kind=='ST':continue
  conduct=True
  if kind=='LD':
   var=e.get('Var','')
   if e.get('Ix')==common_ix and var.startswith('Pause') and override:conduct=(not paused) or manual
   elif var=='ManualMode':conduct=manual if not e.get('Not',False) else not manual
   elif var.startswith('Pause['):conduct=not paused if e.get('Not',False) else paused
   elif var=='M9999':conduct=not emergency if e.get('Not',False) else emergency
  # 他接点とUp命令は導通と仮定し、追加した局所枝だけの配線を検査する。
  if conduct:edge((x,y),(x+1,y))
 maxy=max([e.get('Y',0) for e in row['CLs']]+[e.get('Y',0)+1 for e in row.get('VLs',[])])
 seen={(0,y) for y in range(maxy+1)};todo=list(seen)
 while todo:
  for node in edges[todo.pop()]-seen:seen.add(node);todo.append(node)
 return {e['Var']:((e.get('X',0),e.get('Y',0)) in seen) for e in row['CLs'] if e['__type']=='ST'}
with zipfile.ZipFile(src) as a,zipfile.ZipFile(dst) as z:
 assert a.testzip() is None and z.testzip() is None and a.namelist()==z.namelist()
 changed=[n for n in a.namelist() if a.read(n)!=z.read(n)]
 assert set(changed)=={info['sections']['Destacker_段バラシ'],info['sections']['Output_出力']}
 old={s:[json.loads(l) for l in a.read(info['sections'][s]).decode('utf-8-sig').splitlines()] for s in ['Destacker_段バラシ','Output_出力']}
 new={s:[json.loads(l) for l in z.read(info['sections'][s]).decode('utf-8-sig').splitlines()] for s in old}
 compare_stage(old['Destacker_段バラシ'],new['Destacker_段バラシ'],[])
 assert stagechanges==36
 dpart=info['sections']['Destacker_段バラシ']
 assert a.read(dpart).decode('utf-8-sig').splitlines()[:12]==z.read(dpart).decode('utf-8-sig').splitlines()[:12]
 coils=[int(re.fullmatch(r'Destacker_M\[(\d+)\]',e['Var'])[1]) for e in objects(new['Destacker_段バラシ']) if e.get('__type')=='ST' and re.fullmatch(r'Destacker_M\[\d+\]',e.get('Var',''))]
 assert coils==list(range(1,26))
 expected_rows={p['row']:p for p in info['pause'] if p['common']}
 assert len(expected_rows)==100
 outputpart=info['sections']['Output_出力'];graph_cases=0;added=0;unchanged=0
 beforelines=a.read(outputpart).decode('utf-8-sig').splitlines();afterlines=z.read(outputpart).decode('utf-8-sig').splitlines()
 for rownum,(r1,r2) in enumerate(zip(old['Output_出力'],new['Output_出力'])):
  if rownum not in expected_rows:assert beforelines[rownum]==afterlines[rownum];continue
  p=expected_rows[rownum];x=p['x']
  if p['same_x_manual']:assert beforelines[rownum]==afterlines[rownum];unchanged+=1
  else:
   manuals=[e for e in r2['CLs'] if e.get('__type')=='LD' and e.get('Var')=='ManualMode' and e.get('X',0)==x and e.get('Y',0)==1]
   assert len(manuals)==1 and not manuals[0].get('Not',False)
   oldids={e['Ix'] for e in objects(r1) if 'Ix' in e};assert manuals[0]['Ix'] not in oldids
   remaining=[deepcopy(e) for e in r2['CLs'] if e is not manuals[0]]
   for e in remaining:
    if e.get('Y',0)>=2:e['Y']-=1
   assert remaining==r1['CLs'],'既存接点・コイル・関数の変更'
   assert {k:v for k,v in r1.items() if k not in ['CLs','VLs']}=={k:v for k,v in r2.items() if k not in ['CLs','VLs']}
   # 各旧縦線の両端を別々に座標変換し、追加後の区間を再計算する。
   expected=set()
   for v in r1.get('VLs',[]):
    y=v.get('Y',0);lo=y+1 if y>=1 else y;hi=y+2
    for position in range(lo,hi):expected.add((v['Ix'],v.get('X',0),position))
   actual={(v['Ix'],v.get('X',0),v.get('Y',0)) for v in r2['VLs']}
   assert len(actual)==len(r2['VLs'])
   extra=actual-expected
   assert {(xx,yy) for _,xx,yy in extra}=={(x,0),(x+1,0)} and len(extra)==2
   assert all(ix not in oldids for ix,_,_ in extra)
   assert expected<=actual
   ids=[v['Ix'] for e in r2['CLs'] for v in objects(e) if 'Ix' in v]
   assert len(ids)==len(set(ids)) and not set(ids)&({r2['LRI'],r2['RRI']}|{v['Ix'] for v in r2['VLs']})
   added+=1
  # 追加後のOR枝が所定の区間だけを迂回することを8状態で検査する。
  for pause,manual,emergency in itertools.product([False,True],repeat=3):
   expected=reachable(r1,pause,manual,emergency,p['ix'],True)
   actual=reachable(r2,pause,manual,emergency,p['ix'],False)
   assert expected==actual,(rownum,pause,manual,emergency,expected,actual)
   if emergency:assert not any(actual.values()),(rownum,'非常停止接点の迂回')
   graph_cases+=1
 assert (added,unchanged,graph_cases)==(99,1,800)
 assert hashlib.sha256(src.read_bytes()).hexdigest()==meta['source_sha256']
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==meta['output_sha256']
 result={'検証':'合格','source':str(src),'output':str(dst),'output_sha256':meta['output_sha256'],'段番号変更参照数':stagechanges,'段番号コイル':coils,'0～11行目':'全バイト一致','共通Pause対象':100,'ManualMode追加':99,'既存対応済み':1,'他Pause接点':206,'Output未変更行':'全バイト一致','既存条件・変数・関数・コイル':'座標移動以外保持','縦線と分岐と識別子':'全99行で独立照合','局所配線グラフ状態確認':graph_cases,'同グラフでのM9999迂回':0,'グラフ検査の制約':'他接点・Upを導通とする配線確認。メーカーシミュレータ/実機試験ではない','他構成部品':'208部品全バイト一致','C版原本':'ハッシュ一致','ZIP_CRC':'正常','SysmacStudio読込・全体再ビルド':'未実施','PLC接続と転送':'未実施'}
 (b/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
