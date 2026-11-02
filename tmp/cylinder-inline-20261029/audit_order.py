"""実変数と配列添字で100件を対応付けし、移動で越える命令の依存を調べる。"""
from pathlib import Path
import collections,json,re,sys
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
J=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
RR=J['rows'][J['names']['Output_出力']]

def coil_key(row,kind):
 values=[]
 for c in row['CLs']:
  if c.get('__type')=='ST':
   m=re.fullmatch(r'Output_(A|B|Share)_'+kind+r'\[(\d+)\]',c.get('Var',''))
   if m:values.append((m[1],int(m[2])))
 assert len(values)<=1,values
 return values[0] if values else None

def refs(row):
 reads=set();writes=set()
 def add(target,var):
  if not var or var in ('TRUE','FALSE') or '#' in var:return
  assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\[[A-Za-z0-9_]+\])?(?:\.[A-Za-z_][A-Za-z0-9_]*)*',var),var
  target.add(var)
 for c in row['CLs']:
  kind=c['__type']
  if kind=='LD':add(reads,c.get('Var'))
  elif kind=='ST':
   add(writes,c.get('Var'))
   if c.get('S') or c.get('RS'):add(reads,c.get('Var'))
  elif kind in ('F','FB'):
   for p in c.get('In',[]):add(reads,p.get('Var'))
   for p in c.get('Out',[]):add(writes,p.get('Var'))
   if kind=='FB':add(reads,c['Var']);add(writes,c['Var'])
   if c.get('Name')=='Up':
    reads.add('@Up:'+c.get('Id',''));writes.add('@Up:'+c.get('Id',''))
  else:assert kind in ('HL','VL','EL','VS','END','NEXT'),('未対応命令',kind)
 return reads,writes

def aliases(a,b):
 return a==b or a.startswith(b+'.') or b.startswith(a+'.') or a.startswith(b+'[') or b.startswith(a+'[')

def conflicts(i,k):
 ar,aw=refs(RR[i]);br,bw=refs(RR[k])
 return sorted({(x,y) for xs,ys in ((aw,br|bw),(ar,bw)) for x in xs for y in ys if aliases(x,y)})

def mapping():
 monitors={};controls={};done={}
 for i,row in enumerate(RR):
  if key:=coil_key(row,'Error_M'):
   assert key not in monitors;monitors[key]=i
  if key:=coil_key(row,'M'):
   assert key not in controls;controls[key]=i
   assert i+1<len(RR)
   following=RR[i+1]
   timer=f'Output_{key[0]}_Reset_TON[{key[1]}]'
   assert any(c.get('__type')=='FB' and c.get('Var')==timer for c in following['CLs'])
   assert any(c.get('__type')=='ST' and c.get('Var','').endswith('_Done') for c in following['CLs'])
   done[key]=i+1
 assert len(controls)==len(monitors)==100
 assert controls.keys()==monitors.keys()
 start_mismatches=[];unfiltered_inputs=[]
 for key,m in monitors.items():
  control=RR[controls[key]];completion=RR[done[key]];monitor=RR[m]
  automatic=[c['Var'] for c in monitor['CLs'] if c.get('__type')=='LD' and c.get('Var','').endswith('_Auto[1]')]
  assert len(automatic)==1
  control_auto=[c['Var'] for c in control['CLs'] if c.get('__type')=='LD' and '_Auto[' in c.get('Var','')]
  if automatic[0] not in control_auto:start_mismatches.append({'key':key,'control_auto':control_auto,'monitor_auto':automatic[0]})
  sensors={c['Var'] for c in monitor['CLs'] if c.get('__type')=='LD' and c.get('Var','').startswith(('TimerQ_In_SenCY_','In_SenCY_'))}
  done_sensors={c['Var'] for c in completion['CLs'] if c.get('__type')=='LD' and c.get('Var','').startswith(('TimerQ_In_SenCY_','In_SenCY_'))}
  assert {s.removeprefix('TimerQ_') for s in sensors}=={s.removeprefix('TimerQ_') for s in done_sensors},('到達センサの対応不一致',key)
  if sensors!=done_sensors:unfiltered_inputs.append({'key':key,'completion_sensors':sorted(done_sensors),'monitor_sensors':sorted(sensors)})
  timers=[c['Var'] for c in monitor['CLs'] if c.get('__type')=='FB']
  assert len(timers)==1 and timers[0] in (f'Output_{key[0]}_Error_TON[{key[1]}]',f'Output_{key[0]}_Reset_TON[{key[1]}]')
 assert sorted(monitors.values())==list(range(216,316))
 assert sorted(done.values())==list(range(17,216,2))
 insert={done[key]:key for key in monitors}
 order=[]
 for i in range(len(RR)):
  if i in monitors.values():continue
  order.append(i)
  if i in insert:order.append(monitors[insert[i]])
 assert len(order)==len(set(order))==len(RR)
 positions={old:new for new,old in enumerate(order)}
 crossings=[];hazards=[]
 for i in range(len(RR)):
  for k in range(i+1,len(RR)):
   if positions[i]<positions[k]:continue
   crossings.append([i,k])
   if c:=conflicts(i,k):hazards.append({'before':[i,k],'conflicts':c})
 shared=[]
 for key,m in monitors.items():
  for fb in [c for c in RR[m]['CLs'] if c.get('__type')=='FB']:
   if fb['Var']==f'Output_{key[0]}_Reset_TON[{key[1]}]':shared.append({'key':key,'timer':fb['Var']})
 return {'controls':controls,'monitors':monitors,'done':done,'order':order,'crossings':crossings,'hazards':hazards,'shared_timers':shared,'start_mismatches':start_mismatches,'unfiltered_inputs':unfiltered_inputs}

if __name__=='__main__':
 m=mapping()
 print(json.dumps({'groups':len(m['controls']),'by_side':dict(collections.Counter(k[0] for k in m['controls'])),'crossings':len(m['crossings']),'hazards':m['hazards'],'shared_timers':m['shared_timers']},ensure_ascii=False,indent=2))
 for n in (18,19,217,312):
  print('ROW',n,json.dumps(RR[n],ensure_ascii=False))
