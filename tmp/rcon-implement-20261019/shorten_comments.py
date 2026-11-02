"""RCONの変数・型・配列コメントを短縮し、処理不変のD版を作る。"""
from pathlib import Path
import copy,datetime,hashlib,io,json,re,statistics,sys,zipfile,xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr
sys.stdout.reconfigure(encoding='utf8')
HERE=Path(__file__).parent
SOURCE_DISPLAY=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261019C.smc2')
SOURCE=Path(r'C:\$Recycle.Bin\S-1-5-21-817197267-2385503429-183895641-1001\$R56GCM6.smc2')
DEST=SOURCE_DISPLAY.with_name(SOURCE_DISPLAY.stem[:-1]+'D.smc2');REPORT=DEST.with_suffix('.コメント短縮検証.json')
assert not DEST.exists() and not REPORT.exists(),'同名出力があるため停止'
source=SOURCE.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(source)=='a9c02524336b5876680f943c5d320781817ef84222397870db0d250e1dc5621d','前回C版と内容が異なるため停止'
with zipfile.ZipFile(io.BytesIO(source)) as z:
 assert z.testzip() is None
 original={n:z.read(n) for n in z.namelist()};infos=z.infolist();zipcomment=z.comment
prefix=next(n.rsplit('/',1)[0]+'/' for n in original if n.endswith('.oem'))
gp=prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml';lp=prefix+'a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml';tp=prefix+'4bdcdc10-734d-4589-b299-075e93db9b10.xml'
op=next(n for n in original if n.endswith('.oem'));mp=next(n for n in original if n.endswith('.manifest'))
def dec(b):return b.decode('utf-8-sig')
def enc(b,t):return (b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf8')
def fields(t):return [dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in t.splitlines() if l.startswith('++D=')]
gt,lt,tt,ot,mt=[dec(original[p]) for p in [gp,lp,tp,op,mp]]
g={r['N']:r for r in fields(gt)};loc={r['N']:r for r in fields(lt)}
design=json.loads((HERE.parent/'rcon-bible-20261017'/'manifest.json').read_text(encoding='utf8'))
roles={
 'OUT':'出力指令（PLC→RCON）','IN':'入力情報（RCON→PLC）',
 'SpeedUnit_mm_s':'速度単位 [mm/s/カウント]（1.0/0.1）',
 'RxRaw':'受信値（バイト交換前）','RxWord':'受信ワード（正規化後）',
 'TxWord':'送信ワード候補','TxUInt':'送信UINT候補（実I/Oではない）',
 'LayoutConfirmed':'I/O配置確認済み（初期OFF）','ByteOrderConfirmed':'ワード・バイト順確認済み（初期OFF）',
 'SwapBytes':'上下バイト交換設定（ON=交換）','CommOK':'通信正常（外部判定・固定ON不可）',
 'GwMON_Request':'MON要求（b15）','GwRTE_Request':'通信異常ラッチ解除要求（b13）',
 'GwRun':'GW動作中（RUN/b15）','GwControllerCommLatch':'GW通信異常保持（LERC/b14）',
 'GwAxisCommError':'GW－軸 通信異常（ERRT/b13）','GwManual':'手動モード（MOD/b12）',
 'GwHeavyAlarm':'GW重故障（ALMH/b11）','GwLightAlarm':'GW軽故障（ALML/b10）',
 'GwSystemStop':'システム停止状態（SEMG/b8・監視用）','GwAlarmCode':'GW異常コード（ALMC/b0～7）',
 'AxisLinked':'軸別リンク状態','PowerStateRaw':'電源状態ワード（詳細未確認）',
 'EncodeOK':'軸別変換正常（運転許可とは別）','EncodeError':'軸別変換エラー番号（0=正常）',
 'WriteEnable':'実出力書込み許可（OFF=前値保持・停止不可）','GwApply':'共通出力更新許可（OFF=前値保持）',
 'AxisApply':'軸別出力更新許可（OFF=前値保持）','MotionPermit':'軸別運転許可（外部判定・初期OFF）',
 'GwWritten':'共通出力代入済み（RCON受付とは別）','AxisWritten':'軸別出力代入済み（RCON受付とは別）',
}
out_fields=['目標位置 下位 [0.01mm]','目標位置 上位 [0.01mm]','位置決め幅 下位 [0.01mm]','位置決め幅 上位 [0.01mm]',
 '速度指令 [実機単位]','共通加減速 [0.01G]','押付け制限 [255=100%]','制御信号（DSTR/SON等）']
in_fields=['現在位置 下位 [0.01mm]','現在位置 上位 [0.01mm]','指令電流 下位 [mA]','指令電流 上位 [mA]',
 '現在速度 [実機単位・符号付き]','予約（使用禁止）','軸異常コード','状態信号（PEND/SV等）']
def word_role(u,d,n):
 axes=6 if u==1 else 5
 if n>=8+axes*8:return '用途未確認（今回未使用）'
 if n<8:
  if d=='OUT':return '共通制御（MON/RTE）' if n==0 else '予約（書込禁止）'
  return ['GW状態','軸リンク状態','電源状態0','電源状態1','電源状態2','電源状態3','電源状態4（構成依存）','予約（使用禁止）'][n]
 return f'{(n-8)//8+1}軸目 '+(out_fields if d=='OUT' else in_fields)[(n-8)%8]
def raw(u,d,n):return f'E{1 if u==1 else 5:03d}_{"Out" if d=="OUT" else "In"}_{d}{n:02d}_{"2003" if d=="OUT" else "2004"}_{n+1:02X}'+('' if u==1 else '_1')
comments={};elements={}
for u,axes,words in [(1,6,72),(2,5,56)]:
 p=f'RCON{u}'
 for suffix,c in roles.items():
  name=p+'_'+suffix;assert name in g
  comments[name]=p+' '+c
  if 'EC' not in g[name]:continue
  oldec=ET.fromstring(g[name]['EC']);items={}
  for e in oldec:
   key=e.get('EK');i=int(key[1:-1])
   if suffix in ['RxRaw','RxWord','TxWord','TxUInt']:
    d='IN' if suffix.startswith('Rx') else 'OUT';c=f'{d}{i:02d} '+word_role(u,d,i)
   elif suffix=='PowerStateRaw':c=f'IN{i+2:02d} 電源状態{i}（詳細未確認）'
   else:
    desc={'OUT':'出力指令','IN':'入力情報','AxisLinked':'リンク状態','EncodeOK':'変換正常',
     'EncodeError':'変換エラー番号','AxisApply':'出力更新許可（OFF=前値保持）','MotionPermit':'運転許可（外部判定）',
     'AxisWritten':'出力代入済み（RCON受付とは別）'}[suffix]
    c=f'{i}軸目（No.{i-1}）'+desc
   items[key]=c
  elements[name]=items
 for d in ['OUT','IN']:
  for n in range(words):comments[raw(u,d,n)]=f'{p} {d}{n:02d} '+word_role(u,d,n)
  for row in design['io'][d][:8+8*axes]:
   name=row[0].replace('RCON1_',p+'_',1)
   assert name in g and 'AT' not in g[name]
   n=int(row[2][len(d):]);comments[name]='未割付・不使用 '+row[2]+' '+word_role(u,d,n)
for n,r in g.items():
 if re.fullmatch(r'E005_(?:Out_OUT|In_IN)\d+_200[34]_[0-9A-F]+',n):
  assert 'AT' not in r;comments[n]='旧I/O候補（未割付・不使用）'
assert len(comments)==670
local_comments={
 'ConvWordIndex':'作業用 ワード番号','ConvAxisIndex':'作業用 軸番号（RCON1:1～6／RCON2:1～5）',
 'ConvBase':'作業用 軸先頭ワード番号','ConvDWord':'作業用 32bit分割・結合',
 'ConvPos':'作業用 目標位置 [0.01mm・符号付き]','ConvBand':'作業用 位置決め幅 [0.01mm]',
 'ConvSpeed':'作業用 速度送信値','ConvAccDec':'作業用 共通加減速 [0.01G]','ConvPush':'作業用 押付け制限 [255=100%]',
 'ConvScaled':'作業用 換算後の小数値','ConvWord':'作業用 16bitワード','ConvUnitOK':'作業用 速度単位正常',
 'IAI_M':'旧ダミーマーカー（ST許可ではない）',
}
for n,r in loc.items():
 if r['G']=='VAR_EXTERNAL' and n in comments:local_comments[n]=comments[n]
assert len(local_comments)==293
before_lengths=[];after_lengths=[]
def count(old,new):
 assert new and len(new)<=64,(new,len(new))
 before_lengths.append(len(old));after_lengths.append(len(new))
def table_update(t,mapping):
 result=[];seen=set()
 for line in t.splitlines(keepends=True):
  m=re.search(r'(?:^|\t)N=([^\t\r\n]+)',line)
  if line.startswith('++D=') and m and m[1] in mapping:
   n=m[1];before=dict(k.split('=',1) for k in line.rstrip('\r\n')[2:].split('\t') if '=' in k)
   ending=line[len(line.rstrip('\r\n')):];parts=[]
   for part in line.rstrip('\r\n').split('\t'):
    if part.startswith('Com='):count(part[4:],mapping[n]);part='Com='+mapping[n]
    elif part.startswith('EC=') and n in elements:
     e=ET.fromstring(part[3:])
     assert set(elements[n])=={x.get('EK') for x in e}
     for x in e:count(x.get('C',''),elements[n][x.get('EK')]);x.set('C',elements[n][x.get('EK')])
     part='EC='+ET.tostring(e,encoding='unicode')
    parts.append(part)
   assert 'Com' in before
   line='\t'.join(parts)+ending;seen.add(n)
  result.append(line)
 assert seen==set(mapping)
 return ''.join(result)
ng=table_update(gt,comments);nl=table_update(lt,local_comments)
type_c={
 'ST_RCON_Direct_OUT_Control':'出力 制御信号（15BOOL）',
 'ST_RCON_Direct_IN_Status':'入力 状態信号（12BOOL）',
 'ST_RCON_Direct_OUT_Axis':'1軸分 出力指令（PLC→RCON）',
 'ST_RCON_Direct_IN_Axis':'1軸分 入力情報（RCON→PLC）'}
member_c={
 'Start':'開始指令（DSTR/b0・保持10ms以上）','Home':'原点復帰指令（HOME/b1）',
 'Pause':'一時停止（STP/b2・安全停止ではない）','Reset':'異常リセット指令（RES/b3）','ServoOn':'サーボON指令（SON/b4）',
 'InchingSelect':'インチング選択（JISL/b5・OFF=ジョグ）','JogSpeedSelect':'ジョグ速度切替（JVEL/b6）',
 'JogMinus':'原点方向ジョグ（JOG-/b7）','JogPlus':'反原点方向ジョグ（JOG+/b8）',
 'GainSelect0':'ゲイン選択 下位（GSL0/b10）','GainSelect1':'ゲイン選択 上位（GSL1/b11）',
 'PushEnable':'押付け選択（PUSH/b12・OFF=位置決め）','PushDirection':'押付け方向（DIR/b13）',
 'RelativeMove':'相対移動選択（INC/b14・OFF=絶対）','BrakeRelease':'ブレーキ強制解除（BKRL/b15・落下注意）',
 'PositionDone':'位置決め完了（PEND/b0）','HomeDone':'原点復帰完了（HEND/b1）','Moving':'移動中（MOVE/b2）',
 'Alarm':'軸異常（ALM/b3）','ServoReady':'サーボON状態（SV/b4）','PushMiss':'押付け空振り（PSFL/b5）',
 'OverloadWarning':'過負荷警告等（ALML/b7）','CommandDone':'指令完了（MEND/b8・空振り含む）',
 'Zone1':'ゾーン1内（ZONE1/b12）','Zone2':'ゾーン2内（ZONE2/b13）',
 'ControllerReady':'コントローラー準備完了（CRDY/b14）','EmergencyStop':'非常停止状態（EMGS/b15・監視用）',
 'TargetPos_mm':'目標位置 [mm]','PositionBand_mm':'位置決め幅 [mm]','Speed_mm_s':'指令速度 [mm/s]',
 'AccDec_G':'共通加減速度 [G]','PushLimit_pct':'押付け電流制限 [%]','Control':'出力 制御信号',
 'ActualPos_mm':'現在位置 [mm]','Current_mA':'指令電流 [mA]（RCON-PC）',
 'ActualSpeed_mm_s':'現在速度 [mm/s・符号付き]','AlarmCode':'軸異常コード','Status':'入力 状態信号',
 'DataValid':'入力有効（運転許可とは別）'}
nt=tt
for d in design['defs']:
 name=d['name'];opening=re.search(r'<DataType\b[^>]*\bName="'+name+r'"[^>]*>',nt);assert opening
 end=nt.index('</DataType>',opening.end())+len('</DataType>');block=nt[opening.start():end]
 def update_tag(m):
  tag=m[0];n=re.search(r'\bName="([^"]+)"',tag)[1];c=type_c[name] if n==name else member_c[n]
  old=ET.fromstring(tag if tag.endswith('/>') else tag+'</DataType>').get('Comment','');count(old,c)
  return re.sub(r'\bComment="[^"]*"',lambda _: 'Comment='+quoteattr(c),tag,count=1)
 block=re.sub(r'<DataType\b[^>]*>',update_tag,block)
 nt=nt[:opening.start()]+block+nt[end:]
no=ot;solution=ET.fromstring(ot).find('Entity');assert solution.get('name')==SOURCE_DISPLAY.stem
tag=re.search(r'<Entity\b[^>]*\btype="Solution"[^>]*>',no);newtag=tag[0].replace('name='+quoteattr(SOURCE_DISPLAY.stem),'name='+quoteattr(DEST.stem))
if solution.get('DN')==SOURCE_DISPLAY.stem:newtag=newtag.replace('DN='+quoteattr(SOURCE_DISPLAY.stem),'DN='+quoteattr(DEST.stem))
no=no[:tag.start()]+newtag+no[tag.end():]
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%m/%d/%Y %H:%M:%S')
for id in [Path(gp).stem,Path(lp).stem,Path(tp).stem]:
 tag=re.search(r'<Entity\b[^>]*\bid="'+id+r'"[^>]*>',no);assert tag
 newtag=re.sub(r'dateLastModified="[^"]*"',lambda _:'dateLastModified='+quoteattr(now),tag[0]);no=no[:tag.start()]+newtag+no[tag.end():]
assert 'solutionName='+quoteattr(SOURCE_DISPLAY.stem) in mt
nm=mt.replace('solutionName='+quoteattr(SOURCE_DISPLAY.stem),'solutionName='+quoteattr(DEST.stem),1)
updates={gp:ng,lp:nl,tp:nt,op:no,mp:nm}
def semantic(r):return {k:v for k,v in r.items() if k not in ['Com','EC']}
for old,new,mapping in [(gt,ng,comments),(lt,nl,local_comments)]:
 br,ar=fields(old),fields(new);assert len(br)==len(ar)
 assert [semantic(r) for r in br]==[semantic(r) for r in ar]
 for b,a in zip(br,ar):
  if a['N'] not in mapping:assert b==a
  else:assert a['Com']==mapping[a['N']]
def without_comments(t):
 r=ET.fromstring(t)
 for e in r.iter():e.attrib.pop('Comment',None)
 return ET.tostring(r)
assert without_comments(tt)==without_comments(nt)
gg={r['N']:r for r in fields(ng)};ll={r['N']:r for r in fields(nl)}
for n in local_comments:
 if n in gg:
  assert ll[n]['Com']==gg[n]['Com']
  if 'EC' in gg[n]:assert ll[n]['EC']==gg[n]['EC']
for n,items in elements.items():
 r=gg[n];m=re.match(r'ARRAY\[(\d+)\.\.(\d+)\]',r['D'])
 assert set(items)=={f'[{i}]' for i in range(int(m[1]),int(m[2])+1)}
assert len(after_lengths)==2130,len(after_lengths)
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w') as z:
 z.comment=zipcomment
 for info in infos:z.writestr(copy.copy(info),enc(original[info.filename],updates[info.filename]) if info.filename in updates else original[info.filename])
data=buf.getvalue()
with zipfile.ZipFile(io.BytesIO(data)) as z:
 assert z.testzip() is None and z.namelist()==list(original)
 for n,b in original.items():
  if n not in updates:assert z.read(n)==b,n
 for n,t in updates.items():assert dec(z.read(n))==t
 ET.fromstring(no);ET.fromstring(nm)
assert SOURCE.read_bytes()==source
report={'原本':str(SOURCE),'出力':str(DEST),'原本SHA256':sha(source),'出力SHA256':sha(data),'原本不変':True,
 'グローバルコメント':670,'ローカル・外部参照コメント':293,'型コメント':4,'メンバーコメント':39,
 '配列要素':562,'要素コメント登録':'グローバルと外部参照の両方',
 'コメント総登録数':len(after_lengths),'平均文字数_前':round(statistics.mean(before_lengths),1),'平均文字数_後':round(statistics.mean(after_lengths),1),
 '最大文字数_後':max(after_lengths),'総文字数削減率':round((1-sum(after_lengths)/sum(before_lengths))*100,1),
 '宣言属性・型・初期値・AT':'全て不変','ST本文・ラダー・EtherCAT設定・HMI・タスク':'バイト同一',
 '変更エントリ':list(updates),'不変エントリ':len(original)-len(updates),'ZIP_CRC':'正常','Sysmac読込み・全体再ビルド':'未実施','実機接続・転送':'未実施',
 '注記':'変数・データ型・配列要素のコメントを短縮。ST内の詳説コメントは保持。C版と既存の解説TXTに詳しい説明を残す'}
with DEST.open('xb') as f:f.write(data)
with REPORT.open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
assert sha(DEST.read_bytes())==sha(data) and SOURCE.read_bytes()==source
with zipfile.ZipFile(DEST) as z:assert z.testzip() is None
print(json.dumps(report,ensure_ascii=False,indent=2))
