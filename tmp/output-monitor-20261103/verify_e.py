"""E版の監視接点集合・既存条件保持・分岐接続と監視入口の導通を独立確認する。"""
from pathlib import Path
from copy import deepcopy
import zipfile,json,re,hashlib,sys,collections,itertools
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
info=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
meta=json.loads((b/'build_verification.json').read_text(encoding='utf-8'))
src=Path(meta['source']);dst=Path(meta['output'])
def autos(row):return [e for e in row['CLs'] if e.get('__type')=='LD' and re.fullmatch(r'.+_Auto\[\d+\]',e.get('Var',''))]
def objects(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from objects(v)
 elif isinstance(x,list):
  for v in x:yield from objects(v)
def monitor_input(row,requests,mode,pause,arrived,canonical=None):
 edges=collections.defaultdict(set)
 def add(x,y,two=False):
  edges[x].add(y)
  if two:edges[y].add(x)
 first=autos(row)[0]
 for v in row.get('VLs',[]):
  x=v.get('X',0);y=v.get('Y',0);add((x,y),(x,y+1),True)
 for e in row['CLs']:
  if e.get('__type')=='ST':continue
  x=e.get('X',0);y=e.get('Y',0);conduct=True
  if e.get('__type')=='LD':
   v=e.get('Var','')
   if canonical is not None and e is first:conduct=any(vv in requests for vv in canonical)
   else:
    value=(v in requests) if '_Auto[' in v else mode if v=='AutoMode' else pause if v.startswith('Pause[') else arrived
    conduct=not value if e.get('Not',False) else value
  if conduct:add((x,y),(x+1,y))
 top=max([e.get('Y',0) for e in row['CLs']]+[v.get('Y',0)+1 for v in row.get('VLs',[])])
 seen={(0,y) for y in range(top+1)};todo=list(seen)
 while todo:
  for node in edges[todo.pop()]-seen:seen.add(node);todo.append(node)
 timers=[e for e in row['CLs'] if e.get('__type')=='FB' and e.get('Name')=='TON']
 assert len(timers)==1
 t=timers[0];return (t.get('X',0),t.get('Y',0)) in seen
with zipfile.ZipFile(src) as a,zipfile.ZipFile(dst) as z:
 assert a.testzip() is None and z.testzip() is None and a.namelist()==z.namelist()
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==[info['part']]
 beforelines=a.read(info['part']).decode('utf-8-sig').splitlines();afterlines=z.read(info['part']).decode('utf-8-sig').splitlines()
 assert len(beforelines)==len(afterlines)==316
 old=[json.loads(l) for l in beforelines];new=[json.loads(l) for l in afterlines]
 modified={p['monitor_row']:p for p in info['pairs'] if p['missing'] or p['extra']}
 added=0;renamed=0;states=0;results=[]
 for i,(r1,r2) in enumerate(zip(old,new)):
  if i not in modified:assert beforelines[i]==afterlines[i];continue
  pair=modified[i]
  assert [e['Var'] for e in autos(r2)]==pair['expected']
  original_ids={e['Ix'] for e in objects(r1) if 'Ix' in e}
  newcontacts=[e for e in autos(r2) if e.get('Ix') is not None and e['Ix'] not in original_ids]
  assert all(e.get('X',0)==0 and not e.get('Not',False) for e in newcontacts)
  added+=len(newcontacts)
  existing=[deepcopy(e) for e in r2['CLs'] if e not in newcontacts]
  assert len(existing)==len(r1['CLs'])
  for e1,e2 in zip(r1['CLs'],existing):
   if e1.get('Var') in pair['extra'] and e1.get('__type')=='LD':
    assert e2['Var']==pair['expected'][0];e2['Var']=e1['Var'];renamed+=1
   assert e1==e2,'非対象命令の変更'
  assert {k:v for k,v in r1.items() if k not in ['CLs','VLs']}=={k:v for k,v in r2.items() if k not in ['CLs','VLs']}
  oldw={(v['Ix'],v.get('X',0),v.get('Y',0)) for v in r1.get('VLs',[])}
  neww={(v['Ix'],v.get('X',0),v.get('Y',0)) for v in r2.get('VLs',[])}
  assert oldw<=neww and len(neww)==len(r2.get('VLs',[]))
  count=len(autos(r1));total=len(autos(r2))
  assert {(x,y) for _,x,y in neww-oldw}=={(1,y) for y in range(count-1,total-1)}
  if total>1:
   merge=[v for v in r2['VLs'] if v.get('X',0)==1 and v.get('Y',0)<total-1]
   assert len({v['Ix'] for v in merge})==1 and {v.get('Y',0) for v in merge}==set(range(total-1))
  ids=[v['Ix'] for e in r2['CLs'] for v in objects(e) if 'Ix' in v]
  assert len(ids)==len(set(ids)) and not set(ids)&({r2['LRI'],r2['RRI']}|{v['Ix'] for v in r2.get('VLs',[])})
 assert (len(modified),added,renamed)==(23,22,4)
 for p in info['pairs']:
  drive=new[p['drive_row']];row=new[p['monitor_row']];expected=[e['Var'] for e in autos(drive)]
  assert [e['Var'] for e in autos(row)]==expected
  assert len(expected)==len(set(expected))
  # 全要求の組合せと、自動・一時停止・到達状態を独立した配線グラフで確認。
  for bits in itertools.product([False,True],repeat=len(expected)):
   requests={v for v,on in zip(expected,bits) if on}
   for mode,pause,arrived in itertools.product([False,True],repeat=3):
    result=monitor_input(row,requests,mode,pause,arrived)
    canonical=monitor_input(old[p['monitor_row']],requests,mode,pause,arrived,expected)
    assert result==canonical==bool(requests and mode and not pause and not arrived),(p['monitor_row'],requests,mode,pause,arrived,result,canonical)
    states+=1
  results.append({'駆動行':p['drive_row'],'異常監視行':p['monitor_row'],'Auto接点':expected,'一致':True})
 assert hashlib.sha256(src.read_bytes()).hexdigest()==meta['source_sha256']
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==meta['output_sha256']
 timer_notes=[]
 for p in info['pairs']:
  for e in new[p['monitor_row']]['CLs']:
   if e.get('__type')=='FB' and e.get('Name')=='TON' and '_Error_TON[' not in e.get('Var',''):timer_notes.append({'異常監視行':p['monitor_row'],'タイマ参照':e.get('Var')})
 assert len(timer_notes)==4
 report={'検証':'Auto接点の整合と既存条件保持の確認は合格','output':str(dst),'sha256':meta['output_sha256'],'駆動監視照合組数':100,'修正監視行':23,'接点追加':22,'異なる出力参照の修正':4,'未反映Auto接点':0,'余分なAuto接点':0,'異常タイマ・センサ・停止条件・エラー出力・コメント':'全て保持','局所配線グラフ状態検査':states,'同検査制約':'タイマ入口までの導通を確認。メーカーシミュレータ/時間動作の確認ではない','既存の監視タイマ参照要確認':timer_notes,'その他209部品':'全バイト一致','D版原本':'ハッシュ一致','ZIP_CRC':'正常','Sysmac読込・全体再ビルド':'未実施','PLC接続と転送':'未実施','対応表':results}
 (b/'independent_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='対応表'},ensure_ascii=False))
