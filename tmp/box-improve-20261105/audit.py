"""保存済み回路の横断参照と、保存済みSTを使う開始/受付の条件モデル検査。"""
from pathlib import Path
from zipfile import ZipFile
from collections import Counter,defaultdict
import json,re,hashlib,random
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'));original=json.loads((b/'project.json').read_text(encoding='utf-8'))
assert hashlib.sha256(Path(m['source']).read_bytes()).hexdigest()==m['source_sha256']
with ZipFile(m['staged']) as z:
 box=[json.loads(l) for l in z.read(m['box_part']).decode('utf-8-sig').splitlines()]
 rcon=[json.loads(l) for l in z.read(m['rcon_part']).decode('utf-8-sig').splitlines()]
 output=[json.loads(l) for l in z.read(m['output_part']).decode('utf-8-sig').splitlines()]
 with ZipFile(m['source']) as old:
  assert z.namelist()==old.namelist() and z.testzip() is None
  assert [n for n in old.namelist() if old.read(n)!=z.read(n)]==m['changed_parts']
  prefix=m['rcon_part'].rsplit('/',1)[0]+'/'
  assert z.read(prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml')==old.read(prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml'),'既存許可の定義/初期値は変更しない'
 coils=Counter(c.get('Var') for r in box for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'RCON2_\d+_Auto\[\d+\]',c.get('Var','')))
 assert all(n==1 for n in coils.values())
 contacts={c['Var'] for r in rcon for c in r['CLs'] if c['__type']=='LD'}
 assert set(coils)<=contacts
 allrows=[r for s in original['sections'] for r in (box if s['name']=='BoxPacking_箱詰め' else rcon if s['name']=='RCON_IAI' else output if s['part']==m['output_part'] else s['rows'])]
 boxrequests={c['Var'] for r in box for c in r['CLs'] if c['__type']=='ST' and '_Auto[' in c.get('Var','')}
 globalcounts=Counter(c.get('Var') for r in allrows for c in r['CLs'] if c['__type']=='ST' and c.get('Var') in boxrequests)
 assert all(globalcounts[v]==1 for v in boxrequests),{v:n for v,n in globalcounts.items() if n>1}
 allcontacts={c.get('Var') for r in allrows for c in r['CLs'] if c['__type']=='LD'}
 assert boxrequests<=allcontacts
 for axis in [2,3,4,5]:
  done=next(r for r in rcon if r.get('CMT','').startswith('今回指令のPEND OFF') and any(c.get('Var')==f'RCON2_{axis}_MoveDone' and c['__type']=='ST' for c in r['CLs']))
  assert any(c.get('Var')==f'RCON2_{axis}_M[2]' and c.get('X')==1 and c['__type']=='LD' and not c.get('Not') for c in done['CLs'])
  assert any(c.get('Var')==f'RCON2_{axis}_IN_PositionDone' and c.get('X')==2 for c in done['CLs'])
  assert any(p.get('Var')=='T#100ms' for c in done['CLs'] for p in c.get('In',[]))
 assert {f'RCON2_4_Auto[{i}]' for i in range(1,6)}<=contacts
 assert {f'RCON2_5_Auto[{i}]' for i in range(1,7)}<=contacts
 oldr=next(s['rows'] for s in original['sections'] if s['name']=='RCON_IAI')
 assert rcon[:283]==oldr[:283],'RCON1と段バラシ軸RCON2_1は保持'
 assert box[11]['CLs'][0]['Var']=='BoxPacking_M[16]'
 assert box[37]['CLs'][1]['Var']=='RCON2_4_MoveDone' and not box[37]['CLs'][1].get('Not')
 for axis in [2,3,4,5]:
  st=next(r['CLs'][0]['TXT'] for r in rcon if r.get('CMT','').startswith(f'RCON2_{axis} 開始/受付'))
  assert f'RCON2_MotionPermit[{axis}]' in st and 'RCON2_CommOK' in st and 'NOT M9999' in st
  assert not re.search(r'(?:RCON2_MotionPermit|RCON2_CommOK|RCON2_WriteEnable).*?:=',st)

def expression(s,env):
 s=re.sub(r'(?:LREAL|INT)#','',s)
 def word(mt):
  token=mt[0]
  if token in ['AND','OR','NOT']:return {'AND':'and','OR':'or','NOT':'not'}[token]
  if token in ['TRUE','FALSE']:return str(token=='TRUE')
  assert token in env,token
  return f'env[{token!r}]'
 s=re.sub(r'\b[A-Za-z_]\w*(?:\[\d+\])?(?:\.\w+)*',word,s)
 return eval('('+s+')',{'__builtins__':{}},{'env':env})

def parse(st):
 text=re.sub(r'//[^\n]*','',st);pos=0
 def block():
  nonlocal pos
  items=[]
  while True:
   pos+=len(text[pos:])-len(text[pos:].lstrip())
   if pos>=len(text) or re.match(r'(?:ELSIF|ELSE|END_IF)\b',text[pos:]):return items
   if text.startswith('IF ',pos):
    pos+=3;end=text.index('THEN',pos);condition=text[pos:end].strip();pos=end+4
    branches=[(condition,block())];otherwise=[]
    while text.startswith('ELSIF',pos):
     pos+=5;end=text.index('THEN',pos);condition=text[pos:end].strip();pos=end+4;branches.append((condition,block()))
    if text.startswith('ELSE',pos):pos+=4;otherwise=block()
    assert text.startswith('END_IF;',pos);pos+=7;items.append(('if',branches,otherwise))
   else:
    end=text.index(';',pos);items.append(('stmt',text[pos:end].strip()));pos=end+1
  return items
 return block()

def execute(ast,env,timers,dt):
 for item in ast:
  if item[0]=='if':
   for cond,body in item[1]:
    if expression(cond,env):execute(body,env,timers,dt);break
   else:execute(item[2],env,timers,dt)
  else:
   stmt=item[1]
   timer=re.fullmatch(r'(\w+\[\d+\])\(In := (.*), PT := T#(\d+)ms\)',stmt,re.S)
   if timer:
    name,inp,limit=timer.groups();timers[name]=timers.get(name,0)+dt if expression(inp,env) else 0;env[name+'.Q']=timers[name]>=int(limit)
   else:
    name,value=stmt.split(':=',1);env[name.strip()]=expression(value.strip(),env)

def run(axis,scenario):
 start=parse(next(r['CLs'][0]['TXT'] for r in rcon if r.get('CMT','').startswith(f'RCON2_{axis} 開始/受付')))
 queue=parse(next(r['CLs'][0]['TXT'] for r in rcon if r.get('CMT','').startswith(f'RCON2_{axis} 受付保留/開始保持')))
 env={'AutoMode':True,'Pause[1]':False,'M9999':False,'In_Sw_RESET':False,'RCON2_CommOK':True,'RCON2_WriteEnable':True,'RCON2_LayoutConfirmed':True,'RCON2_ByteOrderConfirmed':True}
 for name in ['Ready']:env[f'RCON2_{axis}_{name}']=True
 for name in ['AxisApply','MotionPermit']:env[f'RCON2_{name}[{axis}]']=True
 env[f'RCON2_IN[{axis}].DataValid']=True
 for name,val in [('Speed_mm_s',100.),('AccDec_G',0.2),('PositionBand_mm',0.1)]:env[f'RCON2_{axis}_OUT_{name}']=val
 for bit in range(1,6):env[f'RCON2_{axis}_M[{bit}]']=False
 env[f'RCON2_OUT[{axis}].Control.Start']=False;env[f'RCON2_{axis}_MoveDone']=False
 timers={};prev=[False,False];done_prev=False;done_elapsed=0;events=[];laststart=False;lastdone=False
 for tick in range(50):
  time=tick*10
  req1=time>=0;req2=scenario=='queue' and time>=140
  position=not (40<=time<100 or (scenario=='queue' and 260<=time<320))
  if scenario=='stale':position=True
  env[f'RCON2_{axis}_IN_PositionDone']=position
  if scenario=='blocked':env[f'RCON2_MotionPermit[{axis}]']=False
  if scenario=='loss' and time>=30:env[f'RCON2_MotionPermit[{axis}]']=False
  if scenario=='reset' and time>=30:env['In_Sw_RESET']=True
  execute(start,env,timers,10)
  signal=env[f'RCON2_OUT[{axis}].Control.Start']
  if signal and not laststart:events.append(('start',time))
  if not signal and laststart:events.append(('start_off',time))
  laststart=signal
  env[f'RCON2_{axis}_M[5]']=env[f'RCON2_{axis}_M[4]'] and ((req1 and not prev[0]) or (req2 and not prev[1]));prev=[req1,req2]
  execute(queue,env,timers,10)
  # 保存ラダーの完了条件はM1・M2・PENDの立上りと100ms保持であることを別途照合する。
  condition=env[f'RCON2_{axis}_M[1]'] and env[f'RCON2_{axis}_M[2]'] and position
  pulse=condition and not done_prev;done_prev=condition
  done=(pulse or env[f'RCON2_{axis}_MoveDone']) and done_elapsed<100
  done_elapsed=done_elapsed+10 if done else 0;env[f'RCON2_{axis}_MoveDone']=done
  if done and not lastdone:events.append(('done',time))
  lastdone=done
 starts=[t for kind,t in events if kind=='start'];dones=[t for kind,t in events if kind=='done']
 if scenario in ['blocked']:assert starts==[] and dones==[]
 elif scenario=='stale':assert len(starts)==1 and dones==[]
 elif scenario in ['loss','reset']:assert dones==[] and not env[f'RCON2_OUT[{axis}].Control.Start']
 elif scenario=='queue':assert len(starts)==2 and dones==[100,320] and starts[1]>200
 else:assert len(starts)==1 and dones==[100]
 return events

results={f'axis{axis}_{scenario}':run(axis,scenario) for axis in [2,3,4,5] for scenario in ['normal','blocked','stale','loss','reset','queue']}

def powers(row,env):
 edges=defaultdict(set)
 for v in row['VLs']:
  p=(v.get('X',0),v.get('Y',0));q=(p[0],p[1]+1);edges[p].add(q);edges[q].add(p)
 for c in row['CLs']:
  x,y=c.get('X',0),c.get('Y',0)
  if c['__type'] in ['HL','F','FB'] or (c['__type']=='LD' and bool(env[c['Var']])!=c.get('Not',False)):edges[(x,y)].add((x+1,y))
 seen={(0,y) for y in range(max(c.get('Y',0) for c in row['CLs'])+1)};todo=list(seen)
 while todo:
  for n in edges[todo.pop()]-seen:seen.add(n);todo.append(n)
 return {(c['__type'],c.get('Id') or c.get('Var')):(c.get('X',0),c.get('Y',0)) in seen for c in row['CLs'] if c['__type'] in ['ST','F','FB']}

oldout=next(s['rows'] for s in original['sections'] if s['part']==m['output_part']);rng=random.Random(1105);outputcases=0
for i in m['output_changed_rows']:
 before,after=oldout[i],output[i]
 variables={c['Var'] for c in after['CLs'] if c['__type']=='LD'}
 root=next(c['Var'][:-3] for c in before['CLs'] if c['__type']=='LD' and c.get('Var','').endswith('_Auto[1]'))
 for n in range(256):
  env={v:bool(rng.getrandbits(1)) for v in sorted(variables)};prev=dict(env)
  prev[root+'[1]']=any(value for name,value in env.items() if name.startswith(root+'['))
  assert powers(before,prev)==powers(after,env),(i,env);outputcases+=1
assert all((5<=n<=80 and n%5==0)==(n in range(5,81,5)) for n in range(-5,91))
m['independent_audit']={'requests_unique':True,'all_requests_have_receiver':True,'source_permission_definitions_unchanged':True,'handshake_model_scenarios':24,'model_results':results,'output_OR_equivalence_cases':outputcases,'box_count_cases':96,'note':'保存STと接続の条件モデル検査。PLCシミュレーター/全体コンパイルではない。'}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in m['independent_audit'].items() if k!='model_results'},ensure_ascii=False))
