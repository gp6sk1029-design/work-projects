"""既存5分岐を保持し、1行のピッチ計算から共通MOVE入力を渡す。"""
from pathlib import Path
from copy import copy,deepcopy
from lxml import etree as E
import zipfile,json,re,hashlib,io,sys,time
sys.stdout.reconfigure(encoding='utf-8')
start=time.monotonic();b=Path(__file__).parent
info=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
src=Path(info['source']);raw=src.read_bytes()
assert hashlib.sha256(raw).hexdigest()==info['sha256'],'A版が外部更新されたため停止'
dest=src.with_name(src.name.replace('20261104A.smc2','20261104B.smc2'))
assert dest!=src and not dest.exists(),'保存先は新規のB版が必要'
pitch='HMI_A_SF_StackPitch_mm'
offset='A_SF_StackStepOffset'
distance='A_SF_StackDelta_mm'
position='A_SF_StackTarget_mm'
pitch_init='LREAL#0.0'
newlocals=[{'N':offset,'D':'LREAL','G':'VAR','Com':'SF積み計算用：カウント−1（1個目は0）'}, {'N':distance,'D':'LREAL','G':'VAR','Com':'SF積み計算用：符号付きピッチ×段数 [mm]'}, {'N':position,'D':'LREAL','G':'VAR','Com':'SF積み計算位置：設定[2]＋ピッチ×(カウント−1) [mm]'}]
globaldef={'N':pitch,'D':'LREAL','R':'1','G':'VAR_GLOBAL','Com':'左SF積みピッチ [mm]。正=位置増、負=位置減。既定0、使用前に設定。1個目は位置設定[2]。'}
external={'N':pitch,'D':'LREAL','G':'VAR_EXTERNAL','Com':globaldef['Com']}
def fields(text):
 return [dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p) for line in text.splitlines() if line.startswith('++D=')]
def definition(d):
 return '++'+'\t'.join(k+'='+d[k] for k in ['D','N','R','G','Com'] if k in d)+'\r\n'
def fun(name,x,inputs,out,index):
 args=[]
 for number,value in enumerate(inputs):args.append({'__type':'PRM','Arg':f'In{number+1}','Ix':index+number+1,'Type':'ANY_NUM','Var':value})
 return {'__type':'F','In':[{'__type':'PF','Arg':'EN'}]+args,'Ix':index,'Name':name,'Out':[{'__type':'PF','Arg':'ENO'},{'__type':'PRM','Arg':'','Ix':index+3,'Type':'ANY_NUM','Var':out}],'X':x}
with zipfile.ZipFile(io.BytesIO(raw)) as zin:
 assert zin.testzip() is None
 part=info['target']['part'];prefix=part.rsplit('/',1)[0]+'/'
 localpart=prefix+'86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml';globalpart=prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml'
 localraw=zin.read(localpart);globalraw=zin.read(globalpart)
 localtext=localraw.decode('utf-8-sig');globaltext=globalraw.decode('utf-8-sig')
 assert '+GN=VAR\tGVT=DefaultGroup' in localtext and '+GN=VAR_EXTERNAL\tGA=External\tGVT=ExternalGroup' in localtext
 assert '+GN=VAR_GLOBAL\tGVT=GlobalNamespaceGroup' in globaltext
 allnames=set()
 for n in zin.namelist():
  try:t=zin.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if t.startswith('[SLWD'):allnames.update(x['N'].casefold() for x in fields(t))
 assert not ({pitch.casefold(),offset.casefold(),distance.casefold(),position.casefold()}&allnames),'新規名の既存定義衝突'
 # ローカル作業値はVAR群の末尾、設定値参照は既存VAR_EXTERNAL群の末尾へ追加する。
 boundary=localtext.index('+GN=VAR_EXTERNAL')
 newlocal=localtext[:boundary]+''.join(definition(v) for v in newlocals)+localtext[boundary:]
 assert newlocal.endswith('\r\n');newlocal+=definition(external)
 assert globaltext.endswith('\r\n');newglobal=globaltext+definition(globaldef)
 localfields=fields(newlocal);globalfields=fields(newglobal)
 assert len(localfields)==len(fields(localtext))+4 and len(globalfields)==len(fields(globaltext))+1
 for old in fields(localtext):assert next(x for x in localfields if x['N']==old['N'])==old
 for old in fields(globaltext):assert next(x for x in globalfields if x['N']==old['N'])==old
 original=zin.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 old=[json.loads(l) for l in lines];assert len(old)==31
 target=17;row=deepcopy(old[target]);changed_moves=[]
 for el in row['CLs']:
  if el.get('__type')!='F' or el.get('Name')!='MOVE':continue
  operands=[p for p in el['In'] if p.get('__type')=='PRM'];assert len(operands)==1
  m=re.fullmatch(r'HMI_RCON1_5_OUT_TargetPos\[(\d+)\]',operands[0]['Var'])
  if m and 2<=int(m[1])<=6:
   changed_moves.append({'Ix':el['Ix'],'旧':operands[0]['Var'],'新':position});operands[0]['Var']=position
 assert len(changed_moves)==5
 row['CMT']='RCON1_5 SF/NG2 降下：OK積み位置をピッチ計算\r\n基準=HMI_RCON1_5_OUT_TargetPos[2]、ピッチ=HMI_A_SF_StackPitch_mm\r\n目標=基準＋ピッチ×(A_SF_CT−1)。カウント1～5の既存分岐とMOVEを保持。\r\n旧位置設定[3]～[6]はこのOK積み位置選択では不使用。\r\nNGキズは位置[7]、NG姿は位置[8]を従来どおり使用。'
 calc={'CLs':[fun('-',0,['A_SF_CT','LREAL#1.0'],offset,0),fun('*',1,[pitch,offset],distance,4),fun('+',2,['HMI_RCON1_5_OUT_TargetPos[2]',distance],position,8)],'CMT':'【左SF積み位置計算】毎スキャン、この位置選択の直前で計算する。\r\n1個目=基準[2]、2個目=基準＋1ピッチ、…、5個目=基準＋4ピッチ。\r\nピッチは符号付きmm。初期値0のため、実際のピッチを設定してから使用する。\r\nこの計算行はRCONの実目標位置へ直接書き込まない。既存の1～5カウント分岐が転送を許可する。','LRI':12,'RRI':13,'VLs':[]}
 # 既存の加算命令と同じ関数レコード形式。LREAL定数により減算からLREALで計算する。
 assert len({v['Ix'] for e in calc['CLs'] for v in [e]+e['In']+e['Out'] if 'Ix' in v})==12
 out=[]
 for i,line in enumerate(lines):
  if i==target:
   out.append(json.dumps(calc,ensure_ascii=False,separators=(',',':'))+'\r\n')
   ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
   out.append(json.dumps(row,ensure_ascii=False,separators=(',',':'))+ending)
  else:out.append(line)
 patch=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8')
 def enc(original,text):return (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
 patches={part:patch,localpart:enc(localraw,newlocal),globalpart:enc(globalraw,newglobal)}
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w') as zout:
  zout.comment=zin.comment
  for e in zin.infolist():zout.writestr(copy(e),patches.get(e.filename,zin.read(e.filename)))
 result=buf.getvalue()
 with zipfile.ZipFile(io.BytesIO(result)) as z:
  assert z.testzip() is None and z.namelist()==zin.namelist()
  changed=[n for n in zin.namelist() if zin.read(n)!=z.read(n)];assert set(changed)==set(patches)
  final=[json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines()]
  assert len(final)==32 and final[target]==calc and final[target+1]==row
 assert src.read_bytes()==raw
 with dest.open('xb') as f:f.write(result)
 assert dest.read_bytes()==result
 report={'source':str(src),'output':str(dest),'source_sha256':info['sha256'],'output_sha256':hashlib.sha256(result).hexdigest(),'changed_parts':changed,'preserved_parts':len(zin.namelist())-3,'target_section':info['target']['name'],'added_calculation_row':17,'old_selection_row':17,'new_selection_row':18,'retained_count_branches':[1,2,3,4,5],'replaced_MOVE_inputs':changed_moves,'pitch_setting':globaldef,'new_local_variables':newlocals,'new_external_reference':external,'formula':'HMI_RCON1_5_OUT_TargetPos[2] + HMI_A_SF_StackPitch_mm * (A_SF_CT - 1)','NG_positions_7_8':'保持','counter_increment_reset':'保持','native_Sysmac_build':'未実施','seconds':round(time.monotonic()-start,3)}
 (b/'build_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
