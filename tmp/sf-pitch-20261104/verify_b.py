"""保存された計算命令と元の位置選択回路を独立に再読込み・数値照合する。"""
from pathlib import Path
from copy import deepcopy
from decimal import Decimal
import zipfile,json,re,hashlib,collections,math,itertools,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
meta=json.loads((b/'build_verification.json').read_text(encoding='utf-8'))
info=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
src=Path(meta['source']);dst=Path(meta['output']);part=info['target']['part']
def fields(text):return [dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in text.splitlines() if l.startswith('++D=')]
def readvar(s,env):
 m=re.fullmatch(r'(?:LREAL|INT)#(.+)',s)
 return float(m[1]) if m and s.startswith('LREAL#') else int(m[1]) if m else env[s]
def calc(row,env):
 for e in sorted(row['CLs'],key=lambda x:x.get('X',0)):
  inputs=[p for p in e['In'] if p.get('__type')=='PRM'];outputs=[p for p in e['Out'] if p.get('__type')=='PRM']
  assert len(inputs)==2 and len(outputs)==1
  a,c=[readvar(p['Var'],env) for p in inputs]
  result=a-c if e['Name']=='-' else a*c if e['Name']=='*' else a+c if e['Name']=='+' else None
  assert result is not None;env[outputs[0]['Var']]=result
 return env['A_SF_StackTarget_mm']
def selection(row,env):
 adjacency=collections.defaultdict(set)
 def add(a,c,two=False):
  adjacency[a].add(c)
  if two:adjacency[c].add(a)
 for v in row['VLs']:
  x=v.get('X',0);y=v.get('Y',0);add((x,y),(x,y+1),True)
 moves=[]
 for e in row['CLs']:
  x=e.get('X',0);y=e.get('Y',0);kind=e['__type'];conduct=True
  if kind=='ST':continue
  if kind=='LD':
   conduct=bool(env[e['Var']]);conduct=not conduct if e.get('Not',False) else conduct
  elif kind=='F' and e.get('Name')=='=':
   p=[p for p in e['In'] if p.get('__type')=='PRM'];conduct=readvar(p[0]['Var'],env)==readvar(p[1]['Var'],env)
  elif kind=='F' and e.get('Name')=='MOVE':moves.append(e)
  else:assert kind=='HL',(kind,e)
  if conduct:add((x,y),(x+1,y))
 maxy=max([e.get('Y',0) for e in row['CLs']]+[v.get('Y',0)+1 for v in row['VLs']])
 seen={(0,y) for y in range(maxy+1)};todo=list(seen)
 while todo:
  for node in adjacency[todo.pop()]-seen:seen.add(node);todo.append(node)
 fired=[]
 for e in moves:
  if (e.get('X',0),e.get('Y',0)) in seen:
   ip=next(p for p in e['In'] if p.get('__type')=='PRM');op=next(p for p in e['Out'] if p.get('__type')=='PRM')
   fired.append((op['Var'],readvar(ip['Var'],env)))
 return fired
with zipfile.ZipFile(src) as a,zipfile.ZipFile(dst) as z:
 assert a.testzip() is None and z.testzip() is None and a.namelist()==z.namelist()
 changed=[n for n in a.namelist() if a.read(n)!=z.read(n)]
 assert changed==meta['changed_parts'] and len(changed)==3
 al=a.read(part).decode('utf-8-sig').splitlines();bl=z.read(part).decode('utf-8-sig').splitlines()
 assert len(al)==31 and len(bl)==32 and al[:17]==bl[:17] and al[18:]==bl[19:]
 old=json.loads(al[17]);new=json.loads(bl[18]);arithmetic=json.loads(bl[17])
 restoration=deepcopy(new);restoration['CMT']=old.get('CMT')
 moveids={52:2,54:3,56:4,58:5,60:6}
 for e in restoration['CLs']:
  if e.get('Ix') in moveids:
   p=next(v for v in e['In'] if v.get('__type')=='PRM')
   assert p['Var']=='A_SF_StackTarget_mm';p['Var']=f'HMI_RCON1_5_OUT_TargetPos[{moveids[e["Ix"]]}]'
 assert restoration==old,'5つのMOVE入力と行コメント以外の元回路に変更'
 assert [e['Name'] for e in arithmetic['CLs']]==['-','*','+']
 assert [e['X'] for e in arithmetic['CLs']]==[0,1,2]
 assert arithmetic['VLs']==[]
 ids=[e['Ix'] for f in arithmetic['CLs'] for e in [f]+f['In']+f['Out'] if 'Ix' in e]
 assert len(ids)==len(set(ids)) and not set(ids)&{arithmetic['LRI'],arithmetic['RRI']}
 prefix=part.rsplit('/',1)[0]+'/'
 localpart=prefix+'86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml';globalpart=prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml'
 for p,newcount in [(localpart,4),(globalpart,1)]:
  before=fields(a.read(p).decode('utf-8-sig'));after=fields(z.read(p).decode('utf-8-sig'))
  assert len(after)==len(before)+newcount
  names={v['N']:v for v in after};assert len(names)==len(after)
  for d in before:assert names[d['N']]==d
  for d in after:
   if d['N'] not in {v['N'] for v in before}:assert 'AT' not in d and 'I' not in d
 localdefs={v['N']:v for v in fields(z.read(localpart).decode('utf-8-sig'))}
 globaldefs={v['N']:v for v in fields(z.read(globalpart).decode('utf-8-sig'))}
 assert globaldefs['HMI_A_SF_StackPitch_mm']['D']=='LREAL' and globaldefs['HMI_A_SF_StackPitch_mm']['R']=='1'
 assert localdefs['HMI_A_SF_StackPitch_mm']['G']=='VAR_EXTERNAL'
 for name in ['A_SF_StackStepOffset','A_SF_StackDelta_mm','A_SF_StackTarget_mm']:
  assert localdefs[name]['D']=='LREAL' and localdefs[name]['G']=='VAR' and 'R' not in localdefs[name]
 mathcases=0;selectcases=0
 bases=['-1000.125','0','100.0','32767.123']
 pitches=['-12.5','0','0.25','7.25','1000.0']
 counts=[-32768,-1,0,1,2,3,4,5,6,32767]
 examples=[]
 for basestr,pitchstr,count in itertools.product(bases,pitches,counts):
  base=float(basestr);pitch=float(pitchstr)
  env={'A_SF_CT':count,'HMI_A_SF_StackPitch_mm':pitch,'HMI_RCON1_5_OUT_TargetPos[2]':base}
  target=calc(arithmetic,env)
  exact=float(Decimal(basestr)+Decimal(pitchstr)*(Decimal(count)-1))
  assert math.isclose(target,exact,rel_tol=1e-12,abs_tol=1e-9)
  mathcases+=1
  for i in range(2,7):env[f'HMI_RCON1_5_OUT_TargetPos[{i}]']=float(Decimal(basestr)+Decimal(pitchstr)*(i-2))
  env['HMI_RCON1_5_OUT_TargetPos[7]']=777.125;env['HMI_RCON1_5_OUT_TargetPos[8]']=888.875
  for judge,detail,sensor,retry,completed in itertools.product([1,9],[4,5,0],[False,True],[False,True],[False,True]):
   run=dict(env);run.update({'ST7_A_Dis2_M[22]':True,'RCON1_3_MoveDone':True,'ST7_A_Dis2_M[23]':False,'Retry[12]':retry,'ST7_A_Dis2_M[27]':completed,'TimerQ_In_Sen_SH_B_Ent':sensor,'Station_A_Data[7].Total_Judge':judge,'Station_A_Data[7].Judgment_Details':detail})
   legacy=selection(old,run);actual=selection(new,run)
   assert len(legacy)==len(actual) and all(x[0]==y[0] and math.isclose(x[1],y[1],rel_tol=1e-12,abs_tol=1e-9) for x,y in zip(legacy,actual)),(basestr,pitchstr,count,judge,detail,sensor,retry,completed,legacy,actual)
   if judge==1 and count not in range(1,6):assert not actual
   selectcases+=1
 examples=[{'count':n,'base_mm':100.0,'pitch_mm':-12.5,'target_mm':100.0-12.5*(n-1)} for n in range(1,6)]
 assert hashlib.sha256(src.read_bytes()).hexdigest()==meta['source_sha256']
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==meta['output_sha256']
 report={'検証':'静的構造と独自PC数値評価は合格','output':str(dst),'sha256':meta['output_sha256'],'新計算行':17,'位置選択行':18,'元カウント5分岐と配置':'保持','NG位置7_8':'全値・条件を保持','その他のラダー行':'一字も変更なし（計算1行挿入で後続表示行番号のみ+1）','既存変数定義':'全て保持','変更MOVE入力':5,'追加グローバル設定':1,'追加ローカル作業値':3,'追加外部参照':1,'他構成部品数':207,'他構成部品':'全バイト一致','計算値検査数':mathcases,'分岐対比検査数':selectcases,'計算例':examples,'評価の限界':'保存JSONから計算と位置選択を独自PC評価。Sysmacコンパイル・メーカーシミュレータ・実機動作ではない','A版原本':'ハッシュ一致','ZIP_CRC':'正常','ピッチ設定':'HMI_A_SF_StackPitch_mm、未設定時の既定値0。使用前に実ピッチを設定','native_Sysmac_build':'未実施','PLC接続と転送':'未実施'}
 (b/'independent_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
