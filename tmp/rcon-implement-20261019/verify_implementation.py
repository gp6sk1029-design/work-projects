"""保存したプロジェクト内のSTそのものをPCモデルで評価する。メーカーのビルドではない。"""
from pathlib import Path
from types import SimpleNamespace
import ast,collections,hashlib,json,math,random,re,sys,zipfile,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf8')
HERE=Path(__file__).parent
report=json.loads((HERE/'implementation.json').read_text(encoding='utf8'))
source=Path(report['原本']); candidate=Path(report['候補'])
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(source.read_bytes())==report['原本SHA256']
assert sha(candidate.read_bytes())==report['出力SHA256']
def fields(t):return [dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in t.splitlines() if l.startswith('++D=')]
with zipfile.ZipFile(candidate) as z,zipfile.ZipFile(source) as old:
 assert z.testzip() is None
 texts={n:z.read(n).decode('utf-8-sig') for n in report['変更エントリ']}
 unchanged=[n for n in old.namelist() if n not in report['変更エントリ']]
 assert len(unchanged)==174
 for n in unchanged:assert old.read(n)==z.read(n),n
 gt=next(t for t in texts.values() if t.startswith('[SLWD') and '+GN=VAR_GLOBAL' in t)
 lt=next(t for t in texts.values() if t.startswith('[SLWD') and '+GN=VAR_EXTERNAL' in t)
 globalmap={r['N']:r for r in fields(gt)}; localmap={r['N']:r for r in fields(lt)}
 body=next(t for t in texts.values() if t.startswith('{'))
 rungs=[json.loads(l) for l in body.splitlines() if l.strip()]
 actualst=[r['CLs'][0]['TXT'] for r in rungs[1:]]
 assert len(actualst)==6
 for b,t in zip(report['blocks'],actualst):assert (HERE/b['file']).read_text(encoding='utf8')==t.replace('\r\n','\n')
 root=ET.fromstring(next(t for n,t in texts.items() if n.endswith('.oem')))
 typesfile=next(n for n in z.namelist() if n.endswith('/4bdcdc10-734d-4589-b299-075e93db9b10.xml'))
 typeroot=ET.fromstring(z.read(typesfile))
 defs={e.get('Name'):{'members':[{'name':m.get('Name'),'type':m.get('BaseType')} for m in e]} for e in typeroot.find('DataType') if e.get('BaseType')=='STRUCT'}
 assert sum(len(defs[n]['members']) for n in defs if n.startswith('ST_RCON_Direct'))==39
 # インラインSTのEID・OEM登録・BookmarkGroupを相互照合。
 section=next(e for e in root.iter('Entity') if e.get('id')=='7b1666c7-ee97-4210-81b2-fed5a6172074')
 entries=[e for e in section.iter('Entity') if e.get('type')=='Inline']
 assert len(entries)==6
 for e,rung in zip(entries,rungs[1:]):
  assert e.get('name')==e.get('trackingId')==rung['CLs'][0]['EID']
  assert any(n.endswith('/'+e.get('id')+'.BookmarkGroup') for n in z.namelist())

# 前回のPC限定構文エンジンから関数群だけを再利用し、旧成果物の書込み処理は実行しない。
oldengine=ast.parse((HERE.parent/'verify_rcon1_st_proposal.py').read_text(encoding='utf8'))
allowed={'checked','swap','signed','expr','assign','tokenize','parse','run','value'}
nodes=[n for n in oldengine.body if isinstance(n,ast.FunctionDef) and n.name in allowed]
nodes+=[n for n in oldengine.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='functions' for t in n.targets)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<前回ST評価エンジン>','exec'),globals())
class BoundedArray(dict):
 """Pythonの辞書と異なり、宣言の外への添字アクセスを許さない。"""
 def __getitem__(self,key):
  assert key in self,('配列読取り範囲外',key,list(self))
  return super().__getitem__(key)
 def __setitem__(self,key,v):
  assert key in self,('配列書込み範囲外',key,list(self))
  super().__setitem__(key,v)
def value(dtype):
 m=re.fullmatch(r'ARRAY\[(\d+)\.\.(\d+)\] OF (\w+)',dtype)
 if m:return BoundedArray({n:value(m[3]) for n in range(int(m[1]),int(m[2])+1)})
 if dtype in defs:return SimpleNamespace(**{m['name']:value(m['type']) for m in defs[dtype]['members']})
 assert dtype in ['BOOL','LREAL','UINT','WORD','DWORD','DINT','INT','UDINT'],dtype
 return False if dtype=='BOOL' else (0.0 if dtype=='LREAL' else 0)
def strip(t):return re.sub(r'//[^\n]*','',t)
blocks=[]
for t in actualst:
 tokens=tokenize(strip(t)); block,end=parse(tokens); assert end==len(tokens);blocks.append(block)
ref=set(re.findall(r'\b(?:RCON[12]_|E001_|E005_|Conv)\w*','\n'.join(strip(t) for t in actualst)))
assert ref<=globalmap.keys()|localmap.keys()
assert len(ref)==292
for n in ref&globalmap.keys():assert localmap[n]['G']=='VAR_EXTERNAL' and localmap[n]['D']==globalmap[n]['D']
controls=json.loads((HERE.parent/'rcon-bible-20261017'/'manifest.json').read_text(encoding='utf8'))['defs'][0]['members']
statuses=json.loads((HERE.parent/'rcon-bible-20261017'/'manifest.json').read_text(encoding='utf8'))['defs'][1]['members']
def raw(u,d,n):return f'E{1 if u==1 else 5:03d}_{"Out" if d=="OUT" else "In"}_{d}{n:02d}_{"2003" if d=="OUT" else "2004"}_{n+1:02X}'+('' if u==1 else '_1')
def environment():
 env={n:value(globalmap[n]['D']) for n in ref&globalmap.keys()}
 env.update({r['N']:value(r['D']) for r in report['newLocals']})
 # STが触らない出力も番兵値で用意し、不用意な書込みを検出。
 for u,words in [(1,72),(2,56)]:
  for n in range(words):env[raw(u,'OUT',n)]=0x5A5A
 return env
def activate(env,u,swapped=False):
 p=f'RCON{u}'; axes=6 if u==1 else 5; words=72 if u==1 else 56
 for name in ['LayoutConfirmed','ByteOrderConfirmed','CommOK']:env[p+'_'+name]=True
 env[p+'_SwapBytes']=swapped;env[p+'_SpeedUnit_mm_s']=0.1
 env[p+'_GwMON_Request']=True
 normal=[0]*words; normal[0]=0x8000;normal[1]=(1<<axes)-1
 for a in range(1,axes+1):
  b=8+(a-1)*8; pos=(-2540 if a%2 else 70025)&0xFFFFFFFF
  current=(-1000 if a%2 else 1000)&0xFFFFFFFF
  normal[b:b+8]=[pos&0xFFFF,pos>>16,current&0xFFFF,current>>16,(-1250)&0xFFFF,0xABCD,0x1234,0xD01B]
  cmd=env[p+'_OUT'][a];cmd.TargetPos_mm=25.40;cmd.PositionBand_mm=0.1;cmd.Speed_mm_s=20.;cmd.AccDec_G=0.2;cmd.PushLimit_pct=50.;cmd.Control.ServoOn=True
 for n,x in enumerate(normal):env[raw(u,'IN',n)]=swap(x) if swapped else x
def permit(env,u):
 p=f'RCON{u}';env[p+'_WriteEnable']=True;env[p+'_GwApply']=True
 for a in range(1,(6 if u==1 else 5)+1):env[p+'_AxisApply'][a]=env[p+'_MotionPermit'][a]=True
def rununit(env,u):
 for b in blocks[(u-1)*3:u*3]:run(b,env)
def physical(env,u):return [env[raw(u,'OUT',n)] for n in range(72 if u==1 else 56)]
tests=collections.Counter()
for u,axes,words in [(1,6,72),(2,5,56)]:
 p=f'RCON{u}';offset=(u-1)*3
 env=environment();rununit(env,u)
 assert physical(env,u)==[0x5A5A]*words
 assert not env[p+'_WriteEnable'] and not env[p+'_CommOK'] and not any(env[p+'_AxisWritten'].values())
 assert not any(env[p+'_IN'][a].DataValid for a in range(1,axes+1));tests['初期状態の実出力不変']+=1
 for swapped in [False,True]:
  env=environment();activate(env,u,swapped);rununit(env,u)
  assert physical(env,u)==[0x5A5A]*words
  for a in range(1,axes+1):
   inp=env[p+'_IN'][a]
   assert math.isclose(inp.ActualPos_mm,-25.4 if a%2 else 700.25,abs_tol=1e-9)
   assert inp.Current_mA==(-1000 if a%2 else 1000) and inp.ActualSpeed_mm_s==-125.0 and inp.AlarmCode==0x1234
   assert inp.DataValid
   for m in statuses:assert getattr(inp.Status,m['name'])==bool(0xD01B&(1<<m['bit']))
   tests['全軸入力復元・両バイト順']+=1
  permit(env,u);run(blocks[offset+2],env)
  assert env[raw(u,'OUT',0)]==(swap(0x8000) if swapped else 0x8000)
  for a in range(1,axes+1):
   b=8+(a-1)*8;expect=[2540,0,10,0,200,20,127,16]
   assert [env[raw(u,'OUT',b+k)] for k in range(8)]==[swap(x) if swapped else x for x in expect]
   assert env[p+'_AxisWritten'][a];tests['全軸出力変換・両バイト順']+=1
  assert all(env[raw(u,'OUT',n)]==0x5A5A for n in list(range(1,8))+list(range(8+8*axes,words)))
  tests['未使用領域不変']+=1
 for mm in [-9999.99,-700.25,-25.4,-0.005,0.,0.005,25.4,700.25,9999.99]:
  env=environment();activate(env,u);env[p+'_OUT'][1].TargetPos_mm=mm;run(blocks[offset+1],env)
  n=math.trunc(mm*100+(0.5 if mm>=0 else -0.5))
  assert env[p+'_TxWord'][8]==n&0xFFFF and env[p+'_TxWord'][9]==(n&0xFFFFFFFF)>>16
  tests['正負位置・境界']+=1
 for m in controls:
  env=environment();activate(env,u)
  for c in controls:setattr(env[p+'_OUT'][1].Control,c['name'],False)
  setattr(env[p+'_OUT'][1].Control,m['name'],True);run(blocks[offset+1],env)
  assert env[p+'_TxWord'][15]==1<<m['bit'];assert not env[p+'_TxWord'][15]&(1<<9);tests['制御15bitと予約bit']+=1
 for m in statuses:
  env=environment();activate(env,u);env[raw(u,'IN',15)]=1<<m['bit'];run(blocks[offset],env)
  for st in statuses:assert getattr(env[p+'_IN'][1].Status,st['name'])==(m['name']==st['name'])
  tests['状態12bit分離']+=1
 invalid=[('unit',0.,1),('TargetPos_mm',float('nan'),2),('TargetPos_mm',float('inf'),2),('TargetPos_mm',-10000.,2),('PositionBand_mm',-1.,3),('Speed_mm_s',-1.,4),('Speed_mm_s',float('inf'),4),('AccDec_G',float('nan'),5),('AccDec_G',656.,5),('PushLimit_pct',201.,6),('jog',True,7)]
 for field,v,error in invalid:
  env=environment();activate(env,u);permit(env,u)
  if field=='unit':env[p+'_SpeedUnit_mm_s']=v
  elif field=='jog':env[p+'_OUT'][1].Control.JogPlus=env[p+'_OUT'][1].Control.JogMinus=True
  else:setattr(env[p+'_OUT'][1],field,v)
  rununit(env,u)
  assert env[p+'_EncodeError'][1]==error and not env[p+'_EncodeOK'][1]
  assert not env[p+'_AxisWritten'][1] and all(env[raw(u,'OUT',n)]==0x5A5A for n in range(8,16))
  tests['不正値で更新保留']+=1
 for flag in ['WriteEnable','LayoutConfirmed','ByteOrderConfirmed','CommOK','GwApply']:
  env=environment();activate(env,u);permit(env,u);env[p+'_'+flag]=False;rununit(env,u)
  if flag=='GwApply':assert env[raw(u,'OUT',0)]==0x5A5A
  else:assert physical(env,u)==[0x5A5A]*words
  tests['全体許可条件の遮断']+=1
 for flag in ['AxisApply','MotionPermit']:
  for a in range(1,axes+1):
   env=environment();activate(env,u);permit(env,u);env[p+'_'+flag][a]=False;rununit(env,u)
   assert not env[p+'_AxisWritten'][a];assert all(env[raw(u,'OUT',n)]==0x5A5A for n in range(8+(a-1)*8,16+(a-1)*8))
   tests['全軸の個別許可条件']+=1
 for unit,expected in [(1.,20),(0.1,200)]:
  env=environment();activate(env,u);env[p+'_SpeedUnit_mm_s']=unit;run(blocks[offset+1],env)
  assert env[p+'_TxWord'][12]==expected;tests['速度単位の違い']+=1
 for pos in [-2147483648,-65537,-1,0,65536,2147483647]:
  env=environment();activate(env,u);bits=pos&0xFFFFFFFF
  env[raw(u,'IN',8)]=bits&0xFFFF;env[raw(u,'IN',9)]=bits>>16;run(blocks[offset],env)
  assert math.isclose(env[p+'_IN'][1].ActualPos_mm,pos*0.01,abs_tol=1e-6);tests['32bit符号復元']+=1
 random.seed(3089+u)
 for i in range(100):
  n=random.randint(-999999,999999);a=1+i%axes;env=environment();activate(env,u);env[p+'_OUT'][a].TargetPos_mm=n/100;run(blocks[offset+1],env)
  b=8+(a-1)*8;assert env[p+'_TxWord'][b]==n&0xFFFF and env[p+'_TxWord'][b+1]==(n&0xFFFFFFFF)>>16
  tests['全軸ランダム位置']+=1
 # 許可を取り下げても、前出力が保持されることを明示検査。停止と誤認しない。
 env=environment();activate(env,u);permit(env,u);rununit(env,u);snapshot=physical(env,u)
 env[p+'_WriteEnable']=False;env[p+'_OUT'][1].TargetPos_mm=100.;rununit(env,u)
 assert physical(env,u)==snapshot;tests['許可OFFは停止でなく前出力保持']+=1

# 共通ローカルを順番に使っても2台の指令・入力が混ざらないことを確認。
for order in [(False,True),(True,False),(False,False),(True,True)]:
 env=environment();activate(env,1,order[0]);activate(env,2,order[1]);permit(env,1);permit(env,2)
 env['RCON1_OUT'][6].TargetPos_mm=700.25;env['RCON2_OUT'][5].TargetPos_mm=-25.4
 for b in blocks:run(b,env)
 for u,a,expected in [(1,6,[4489,1]),(2,5,[62996,65535])]:
  b=8+(a-1)*8
  assert [env[raw(u,'OUT',b+n)] for n in range(2)]==[swap(x) if order[u-1] else x for x in expected]
 tests['2台同時・共有作業変数・独立バイト順']+=1
out={'PC模擬チェック合計':sum(tests.values()),'内訳':dict(tests),'実装STと抽出ST一致':True,'全参照名照合':len(ref),
 'ZIP_CRC':'正常','OEM_ST参照':'6件一致','既存不変エントリ':len(unchanged),'原本不変':sha(source.read_bytes())==report['原本SHA256'],
 'Sysmac Studio読込み・ビルド':'未実施','メーカーシミュレーター・実機':'未実施',
 '注意':'限定構文の独自PC評価。Sysmacのコンパイル・CPUでの丸め/実行・実機安全確認の代用ではない。'}
(HERE/'検証結果.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(out,ensure_ascii=False,indent=2))
