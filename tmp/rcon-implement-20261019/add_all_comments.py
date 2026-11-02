"""RCON関連の宣言コメントと配列要素・型コメントだけを編集し、C版を生成する。"""
from pathlib import Path
import copy,datetime,hashlib,io,json,re,sys,zipfile,xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr
sys.stdout.reconfigure(encoding='utf8')
HERE=Path(__file__).parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261019B.smc2')
DEST=SOURCE.with_name(SOURCE.stem[:-1]+'C.smc2')
SUMMARY=DEST.parent/'RCON_STコメント追加_20261019C.txt'
CATALOG=DEST.parent/'RCON_ST全コメント一覧_20261019C.txt'
REPORT=DEST.with_suffix('.コメント検証.json')
for p in [DEST,SUMMARY,CATALOG,REPORT]:assert not p.exists(),f'同名出力が存在：{p}'
design=json.loads((HERE.parent/'rcon-bible-20261017'/'manifest.json').read_text(encoding='utf8'))
sha=lambda b:hashlib.sha256(b).hexdigest()
def fields(t):return [dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in t.splitlines() if l.startswith('++D=')]
def decode(b):return b.decode('utf-8-sig')
def encode_like(b,t):return (b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf8')
def raw(u,d,n):return f'E{1 if u==1 else 5:03d}_{"Out" if d=="OUT" else "In"}_{d}{n:02d}_{"2003" if d=="OUT" else "2004"}_{n+1:02X}'+('' if u==1 else '_1')
source=SOURCE.read_bytes()
with zipfile.ZipFile(io.BytesIO(source)) as z:
 assert z.testzip() is None
 original={n:z.read(n) for n in z.namelist()}; infos=z.infolist();zipcomment=z.comment
prefix=next(n.rsplit('/',1)[0]+'/' for n in original if n.endswith('.oem'))
gp=prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml'
lp=prefix+'a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml'
tp=prefix+'4bdcdc10-734d-4589-b299-075e93db9b10.xml'
op=next(n for n in original if n.endswith('.oem'));mp=next(n for n in original if n.endswith('.manifest'))
gt,lt,tt,ot,mt=[decode(original[n]) for n in [gp,lp,tp,op,mp]]
globals_before=fields(gt); globalmap={r['N']:r for r in globals_before}
locals_before=fields(lt); localmap={r['N']:r for r in locals_before}
comments={}; elements={}; builtin={
 'BOOL':'ON/OFFの真偽値（TRUE/ FALSE）',
 'INT':'符号付き16bit整数','UINT':'符号なし16bit整数（0～65535）',
 'DINT':'符号付き32bit整数','UDINT':'符号なし32bit整数',
 'WORD':'16bitのビット列','DWORD':'32bitのビット列','LREAL':'小数を扱う64bit実数'}
def meaning(u,d,n):
 axes=6 if u==1 else 5
 if n<8+8*axes:return design['io'][d][n][1]
 return f'【{d}{n:02d}】軸データの対象外・用途未確認。実機の占有情報を確認するまで意味を決めない'
roles={
 'OUT':'PLC→RCONの1軸分指令をまとめた構造体配列。位置mm・速度mm/s・加減速G・押付け%。入力値を②で変換し、③の許可時だけ実出力へ代入',
 'IN':'RCON→PLCの1軸分取得値をまとめた構造体配列。①で位置mm・速度mm/s・電流mA・状態を復元。DataValid=FALSEの値で運転しない',
 'SpeedUnit_mm_s':'設定：速度1カウント当たりのmm/s。LREALで実機設定に一致する1.0または0.1を指定。初期0は未確認で、軸出力を更新しない',
 'RxRaw':'入力：実I/OのUINTを①でコピーした読取り専用の生通信配列。1要素16bit。バイト交換前で、ここへの代入は実入力を変更しない',
 'RxWord':'入力：RxRawをWORDへ変換し、必要なバイト交換を適用した論理ワード配列。取説のbitをこの値から取り出す。バイト順の確認は別途必要',
 'TxWord':'出力候補：②で数値・制御BOOLをまとめた論理WORD配列。まだ実I/Oではない。位置/幅の上下ワード、速度、加減速、制御を保持',
 'TxUInt':'出力候補：TxWordへ通信のバイト順を適用したUINT配列。③の確認・許可条件がそろったときだけE始まりの実出力へ代入',
 'LayoutConfirmed':'確認用BOOL：全軸直接数値指定・共通8ワード・各軸8ワード・軸順・占有を実機と照合した場合のみTRUE。初期FALSE。運転許可の代用ではない',
 'ByteOrderConfirmed':'確認用BOOL：ゼロ以外の既知位置と既知bitで上下ワード順・バイト順を実機照合した場合のみTRUE。初期FALSE。値が見えるだけでは確認にならない',
 'SwapBytes':'設定BOOL：TRUEで各16bitワード内の上位/下位バイトを交換。上下ワード自体の順は入れ替えない。初期FALSEは交換不要を確認済みという意味ではない',
 'CommOK':'外部で作成する通信正常BOOL：CPU/当該EtherCATノードの実通信状態から判定。初期FALSE。TRUE固定や受信数値だけの判定は禁止。今回STは生成しない',
 'GwMON_Request':'共通出力要求BOOL：TRUEでゲートウェイのMONを論理b15にセットする送信候補を作る。実送信にはGwApply等が必要。初期FALSE。安全停止ではない',
 'GwRTE_Request':'共通出力要求BOOL：TRUEで通信異常ラッチ解除RTEを論理b13にセットする送信候補を作る。実送信にはGwApply等が必要。初期FALSE',
 'GwRun':'共通入力BOOL：①で共通状態ワードIN00の論理b15/RUNを取り出す。ゲートウェイ動作中の応答。これだけで運転可能と判断しない',
 'GwControllerCommLatch':'共通入力BOOL：IN00の論理b14/LERC。運転中のコントローラー通信異常の保持情報。現在の軸通信異常GwAxisCommErrorと区別する',
 'GwAxisCommError':'共通入力BOOL：IN00の論理b13/ERRT。ゲートウェイと軸間の通信異常。TRUE時はIN.DataValidをFALSEにする。出力更新保留は停止ではない',
 'GwManual':'共通入力BOOL：IN00の論理b12/MOD。MANUスイッチ選択状態。自動運転許可そのものではない',
 'GwHeavyAlarm':'共通入力BOOL：IN00の論理b11/ALMH。ゲートウェイの再起動が必要な異常情報。軸Status.Alarmとは別',
 'GwLightAlarm':'共通入力BOOL：IN00の論理b10/ALML。ゲートウェイの軽微異常情報。軸Status.OverloadWarningとは別',
 'GwSystemStop':'共通入力BOOL：IN00の論理b8/SEMG。システムSTOP入力に関する停止状態のモニター。安全回路・非常停止判定の代用品ではない',
 'GwAlarmCode':'共通入力UINT：IN00の論理b0～7/ALMCを取り出したゲートウェイ異常コード。各軸IN.AlarmCodeとは別のコード',
 'AxisLinked':'軸別入力BOOL配列：①でIN01の各リンクbitを取得。[1]はb0/実機軸No.0。TRUEはリンク情報でありサーボON・安全許可ではない',
 'PowerStateRaw':'共通入力WORD配列：[0]～[4]にIN02～IN06の論理ワードを保存。電源状態等の詳細意味は構成依存のため、今回ビット分解しない',
 'EncodeOK':'軸別診断BOOL配列：②で指令値を通信形式へ変換できたときTRUE。EncodeError=0に対応。機械のストローク・安全・運転許可の保証ではない',
 'EncodeError':'軸別診断UINT配列：0=変換可能、1=速度単位、2=位置、3=幅、4=速度、5=加減速、6=押付け、7=ジョグ両方向。非0でその軸の出力更新を保留',
 'WriteEnable':'書込み全体許可BOOL：TRUEのとき③の実I/O代入を検討する。初期FALSE。OFFは更新保留で前のStart/ServoOn等が残り得る。停止指令ではない',
 'GwApply':'共通出力更新許可BOOL：全体条件を満たすときOUT00のMON/RTEを実I/Oへ代入。初期FALSE。OFFは前出力保持であり安全停止ではない',
 'AxisApply':'軸別更新許可BOOL配列：指定軸の数値・制御の8ワードを一組で代入する許可。全体条件・EncodeOK・DataValid・MotionPermitも必要。初期FALSE',
 'MotionPermit':'機械側で作成する軸別運転許可BOOL配列：ストローク・到達先・速度・原点・干渉・異常・安全条件等を確認。初期FALSE。今回STは生成せず、TRUE固定禁止',
 'GwWritten':'内部診断BOOL：③で共通出力変数へ代入したPLCサイクルのみTRUE。RCONの受信・受付・正常応答を保証する信号ではない',
 'AxisWritten':'軸別内部診断BOOL配列：③でその軸の実出力8ワードへ代入したPLCサイクルのみTRUE。RCONの受付や移動完了を意味しない',
}
for u,axes,words in [(1,6,72),(2,5,56)]:
 p=f'RCON{u}'; node=1 if u==1 else 5
 for suffix,desc in roles.items():
  name=p+'_'+suffix;assert name in globalmap,name
  comments[name]=f'{p}/Node{node}：'+desc
 for name,row in globalmap.items():
  if name.startswith(p+'_') and name not in comments:
   assert row['D']=='UINT' and 'Raw' in name and 'AT' not in row,name
   old=row.get('Com','').replace('（未割付・直接数値指定の設計用）','')
   comments[name]='旧設計用・未割付UINT：'+old+'。今回STでは不使用。実通信はE始まりのI/O変数を使い、重複割付しない'
 for d in ['OUT','IN']:
  for n in range(words):
   name=raw(u,d,n);assert name in globalmap
   desc=meaning(u,d,n)
   if d=='OUT':action='③の許可時に更新' if n==0 or 8<=n<8+axes*8 else '今回STは書換えない'
   else:action='①で読取り。実入力への代入禁止'
   comments[name]=f'{p}/Node{node} 実I/O UINT（16bit）：{desc}。{action}。単位/bitは正規化した論理値で解釈'
 # 配列要素のコメントを既存形式ECで付ける。構造体のメンバー説明は型側を継承する。
 for suffix in roles:
  name=p+'_'+suffix;row=globalmap[name]
  arr=re.fullmatch(r'ARRAY\[(\d+)\.\.(\d+)\] OF (\w+)',row['D'])
  if not arr:continue
  items={}
  for i in range(int(arr[1]),int(arr[2])+1):
   if suffix in ['RxRaw','RxWord','TxWord','TxUInt']:
    d='IN' if suffix.startswith('Rx') else 'OUT'
    stage={'RxRaw':'受信コピー・バイト交換前のUINT','RxWord':'正規化後の論理WORD','TxWord':'変換後の論理WORD候補','TxUInt':'実I/O代入前のUINT候補'}[suffix]
    desc=f'{p} {stage}：'+meaning(u,d,i)
    if d=='OUT' and 1<=i<=7:desc+='。実出力には今回書き込まない'
   elif suffix=='PowerStateRaw':desc=f'{p} 共通入力IN{i+2:02d}の論理WORD。構成依存の生情報で、今回ビットの意味を確定しない'
   else:
    start=8+(i-1)*8;lead=f'{p} {i}軸目（実機軸No.{i-1}、ワード{start:02d}～{start+7:02d}）：'
    desc=lead+{
     'OUT':'PLC→RCON指令。位置mm・速度mm/s・加減速G等を設定。直接実I/Oではない',
     'IN':'RCON→PLC取得値・状態。DataValid確認前の値で運転しない',
     'AxisLinked':f'リンク応答IN01の論理b{i-1}。サーボON状態とは別',
     'EncodeOK':'TRUE=数値変換可能。安全・機械範囲・運転許可とは別',
     'EncodeError':'変換エラー番号。0正常、1単位、2位置、3幅、4速度、5加減速、6押付け、7ジョグ両方向',
     'AxisApply':'この軸の8ワードの更新許可。初期FALSE。OFFでも前出力が残る',
     'MotionPermit':'機械側で作成する運転許可。初期FALSE。今回STで生成しない',
     'AxisWritten':'実出力へ代入したサイクルだけTRUE。RCON受付・移動完了とは別',
    }[suffix]
   items[f'[{i}]']=desc
  elements[name]=items

# 同じ系列のATなし旧自動生成名も、現行I/Oと誤認しないよう注記する。
for name,row in globalmap.items():
 if re.fullmatch(r'E005_(?:Out_OUT|In_IN)\d+_200[34]_[0-9A-F]+',name):
  assert 'AT' not in row,name
  comments[name]='未割付の旧I/O候補UINT（16bit）。今回STは不使用。現在のNode5実I/Oは末尾_1付き変数。ATなしのため実通信値として使用しない。個別の割付意味は未確定'
assert len(comments)==670,len(comments)
local_comments={
 'ConvWordIndex':'作業用INT：ワード配列を順番に処理する添字。RCON1受信0～71、RCON2受信0～55。指令値として設定しない',
 'ConvAxisIndex':'作業用INT：現在処理中の軸番号。RCON1は1～6、RCON2は1～5。実機軸No.はこの値-1。指令値として設定しない',
 'ConvBase':'作業用INT：軸の先頭ワード番号。8+(軸番号-1)×8で計算。1軸目8、2軸目16、…、6軸目48',
 'ConvDWord':'作業用DWORD：32bitのビット列。上位/下位16bitの分割・結合に使用。位置や電流の負数のビットを壊さず扱う',
 'ConvPos':'作業用DINT：目標位置mmを100倍して四捨五入した0.01mm単位の符号付き32bit整数。例25.40mm→2540',
 'ConvBand':'作業用UDINT：位置決め幅mmを100倍して四捨五入した0.01mm単位の非負内部整数。例0.10mm→10。内部設計上の型',
 'ConvSpeed':'作業用UINT：指令速度mm/s÷SpeedUnit_mm_sを四捨五入した送信整数。20mm/sで単位0.1なら200、単位1.0なら20',
 'ConvAccDec':'作業用UINT：加速・減速共通G値を100倍して四捨五入した送信整数。例0.20G→20。加速/減速の個別値ではない',
 'ConvPush':'作業用UINT：押付け電流制限%×255÷100の小数部を切り捨てた送信整数。例50%→127。実機の許容上限は別途確認',
 'ConvScaled':'作業用LREAL：mm等を通信整数の単位へ換算した四捨五入前の小数値。位置は正値+0.5/負値-0.5をTRUNCへ渡す',
 'ConvWord':'作業用WORD：1ワード分のバイト交換・UINT変換に用いる16bitビット列。送信候補の変換中だけ使用',
 'ConvUnitOK':'作業用BOOL：処理中ユニットの速度単位が1.0または0.1ならTRUE。機械の運転許可ではない。2台を順番に処理するたび再計算',
 'IAI_M':'既存ダミー回路用BOOL：RCON_IAI冒頭のP_Off接点でOFFになるマーカー。追加した6つのSTの実行許可・実I/O書込み許可ではない',
}
assert all(n in localmap for n in local_comments)
for name,row in localmap.items():
 if row['G']=='VAR_EXTERNAL' and name in comments:local_comments[name]=comments[name]
assert len(local_comments)==293,len(local_comments)
def ecxml(items):
 e=ET.Element('ECs')
 for k,c in items.items():ET.SubElement(e,'EC',EK=k,C=c)
 return ET.tostring(e,encoding='unicode',short_empty_elements=True)
def replace_table(t,cmts):
 result=[];touched=set()
 for l in t.splitlines(keepends=True):
  m=re.search(r'(?:^|\t)N=([^\t\r\n]+)',l)
  if l.startswith('++D=') and m and m[1] in cmts:
   name=m[1]; ending=l[len(l.rstrip('\r\n')):]
   parts=[p for p in l.rstrip('\r\n').split('\t') if not p.startswith('Com=') and not (name in elements and p.startswith('EC='))]
   c=cmts[name];assert all(x not in c for x in ['\t','\r','\n']) and len(c)<=255,(name,len(c))
   parts.append('Com='+c)
   if name in elements:parts.append('EC='+ecxml(elements[name]))
   l='\t'.join(parts)+ending;touched.add(name)
  result.append(l)
 assert touched==set(cmts),set(cmts)-touched
 return ''.join(result)
ng=replace_table(gt,comments);nl=replace_table(lt,local_comments)

# データ型の型名・幅・メンバー順は保全し、Comment属性だけを置換する。
type_comments={
 'ST_RCON_Direct_OUT_Control':'PLC→RCONの1軸分制御BOOL群（15メンバー）。②で制御ワードへまとめる。予約b9は0。指令でありRCONからの状態応答ではない',
 'ST_RCON_Direct_IN_Status':'RCON→PLCの1軸分状態BOOL群（12メンバー）。①で状態ワードから取り出す。運転許可や安全回路とは別。OUT.Controlの指令と区別する',
 'ST_RCON_Direct_OUT_Axis':'PLC→RCONの1軸分指令。5つのLREAL値をmm/mm毎秒/G/%の工学単位で保持し、Controlを含む。通信PDO直結用ではなく内部構造体',
 'ST_RCON_Direct_IN_Axis':'RCON→PLCの1軸分取得情報。現在位置・現在速度・電流・異常・状態と内部判定DataValidを保持。生UINTを復元した内部構造体',
}
axis_member_comments={
 'ST_RCON_Direct_OUT_Axis':{
  'TargetPos_mm':'OUT指令/LREAL（小数）/mm：目標位置。25.40→送信整数2540（0.01mm）。Control.RelativeMove=FALSEは絶対位置、TRUEは相対移動量。機械範囲は別途検査',
  'PositionBand_mm':'OUT指令/LREAL（小数）/mm：位置決め幅。0.10→送信整数10（0.01mm）。非負値。実機に適した幅・許容範囲は別途確認',
  'Speed_mm_s':'OUT指令/LREAL（小数）/mm/s：指令速度。送信値=この値÷実機速度単位1.0または0.1。例20mm/s÷0.1=200。実機の速度上限は別途確認',
  'AccDec_G':'OUT指令/LREAL（小数）/G：加速と減速に共通で使う値。0.20G→送信整数20（0.01G）。加速と減速の個別指定ではない',
  'PushLimit_pct':'OUT指令/LREAL（小数）/%：押付け電流制限。送信値=この値×255÷100の切捨て。例50%→127。通常位置決め/押付けの選択はControl.PushEnable',
  'Control':'OUT指令/ST_RCON_Direct_OUT_Control：ServoOn・Start等の15個のBOOLを入れる構造体。②で制御WORDへ組立、③の許可時だけ実I/Oへ代入',
 },
 'ST_RCON_Direct_IN_Axis':{
  'ActualPos_mm':'IN取得/LREAL（小数）/mm：上下2ワードを符号付き32bitへ復元して0.01倍した現在位置。負位置を保持。DataValidがFALSEなら運転判断に使わない',
  'Current_mA':'IN取得/DINT（符号付き32bit整数）/mA：上下2ワードから復元した電流。RCON-PCでは指令電流であり、実測トルク・実測押付力ではない',
  'ActualSpeed_mm_s':'IN取得/LREAL（小数）/mm/s：符号付き16bit速度×実機速度単位。負方向の符号を保持。速度単位が未確認なら前値保持、DataValidはFALSE',
  'AlarmCode':'IN取得/UINT（符号なし16bit整数）：軸のアラームコード。共通GwAlarmCodeや簡易コードとは別。Status.Alarmと併せて原因を確認',
  'Status':'IN取得/ST_RCON_Direct_IN_Status：位置決め完了・サーボON等の12個の状態BOOL。①で状態WORDから取り出す。指令Controlとは別物',
  'DataValid':'内部判定/BOOL：通信・割付・バイト順・速度単位・RUN・軸リンク等の条件がそろうとTRUE。直接受信bitではない。初期FALSE。安全/運転許可の保証ではない',
 }}
alltypecomments={}
for d in design['defs']:
 name=d['name'];cms={name:type_comments[name]}
 for m in d['members']:
  if 'bit' in m:
   direction='OUT指令' if d['dir']=='OUT' else 'IN取得'
   cms[m['name']]=f'{direction}/BOOL（ON/OFF）/論理b{m["bit"]}/{m["signal"]}：{m["explain"]}'
  else:cms[m['name']]=axis_member_comments[name][m['name']]
 alltypecomments[name]=cms
nt=tt
for name,cms in alltypecomments.items():
 opening=re.search(r'<DataType\b[^>]*\bName="'+name+r'"[^>]*>',nt);assert opening
 end=nt.index('</DataType>',opening.end())+len('</DataType>')
 block=nt[opening.start():end]; seen=set()
 def replace_tag(m):
  tag=m[0]; nm=re.search(r'\bName="([^"]*)"',tag)
  assert nm and nm[1] in cms,nm[1] if nm else tag
  c=cms[nm[1]];assert len(c)<=255
  assert re.search(r'\bComment="[^"]*"',tag)
  seen.add(nm[1]);return re.sub(r'\bComment="[^"]*"',lambda _: 'Comment='+quoteattr(c),tag,count=1)
 newblock=re.sub(r'<DataType\b[^>]*>',replace_tag,block)
 assert seen==set(cms)
 nt=nt[:opening.start()]+newblock+nt[end:]

# 表示名と編集日時のメタデータだけC版へ更新。
root=ET.fromstring(ot); solution=root.find('Entity');oldname=solution.get('name');assert oldname==SOURCE.stem
no=ot
tag=re.search(r'<Entity\b[^>]*\btype="Solution"[^>]*>',no);assert tag
newtag=tag[0].replace('name='+quoteattr(oldname),'name='+quoteattr(DEST.stem))
if solution.get('DN')==oldname:newtag=newtag.replace('DN='+quoteattr(oldname),'DN='+quoteattr(DEST.stem))
no=no[:tag.start()]+newtag+no[tag.end():]
modified=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%m/%d/%Y %H:%M:%S')
for id in ['f07dd06c-505c-431b-b9fc-098949805b4e','a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10','4bdcdc10-734d-4589-b299-075e93db9b10']:
 tag=re.search(r'<Entity\b[^>]*\bid="'+id+r'"[^>]*>',no);assert tag
 newtag=re.sub(r'dateLastModified="[^"]*"',lambda _: 'dateLastModified='+quoteattr(modified),tag[0])
 no=no[:tag.start()]+newtag+no[tag.end():]
assert 'solutionName='+quoteattr(oldname) in mt
nm=mt.replace('solutionName='+quoteattr(oldname),'solutionName='+quoteattr(DEST.stem),1)
updates={gp:ng,lp:nl,tp:nt,op:no,mp:nm}

# 全宣言の実動作属性の同一性と、全コメントの網羅性を検査する。
def no_comment_fields(r):return {k:v for k,v in r.items() if k not in ['Com','EC']}
for before,after,cmts in [(gt,ng,comments),(lt,nl,local_comments)]:
 br,ar=fields(before),fields(after);assert len(br)==len(ar)
 assert [no_comment_fields(r) for r in br]==[no_comment_fields(r) for r in ar]
 for b,a in zip(br,ar):
  if a['N'] not in cmts:assert a==b
  else:
   assert a['Com']==cmts[a['N']] and a['Com'].strip()
   if a['N'] in elements:
    parsed={e.get('EK'):e.get('C') for e in ET.fromstring(a['EC'])}
    assert parsed==elements[a['N']]
    am=re.fullmatch(r'ARRAY\[(\d+)\.\.(\d+)\] OF (\w+)',a['D'])
    assert set(parsed)=={f'[{i}]' for i in range(int(am[1]),int(am[2])+1)}
def strip_type_comments(t):
 r=ET.fromstring(t)
 for e in r.iter():e.attrib.pop('Comment',None)
 return ET.tostring(r)
assert strip_type_comments(tt)==strip_type_comments(nt),'型の実動作属性が変わった'
troot=ET.fromstring(nt)
for name,cms in alltypecomments.items():
 e=next(e for e in troot.iter('DataType') if e.get('Name')==name)
 assert e.get('Comment')==cms[name]
 for member in e:assert member.get('Comment')==cms[member.get('Name')]
assert ET.fromstring(no).find('Entity').get('name')==DEST.stem
ET.fromstring(nm)
result=io.BytesIO()
with zipfile.ZipFile(result,'w') as z:
 z.comment=zipcomment
 for info in infos:z.writestr(copy.copy(info),encode_like(original[info.filename],updates[info.filename]) if info.filename in updates else original[info.filename])
data=result.getvalue()
with zipfile.ZipFile(io.BytesIO(data)) as z:
 assert z.testzip() is None and z.namelist()==list(original)
 for n,b in original.items():
  if n not in updates:assert z.read(n)==b,n
 for n,t in updates.items():assert decode(z.read(n))==t
assert SOURCE.read_bytes()==source,'作業中にB版が更新されたため中止'

# コメント一覧は読みやすい確認用TXTとして保存し、プロジェクト内コメントと照合する。
catalog=['RCON関連 全コメント一覧／20261019C','方向はPLC基準：OUT=PLC→RCON、IN=RCON→PLC。','コメント追加のみ。名前・型・初期値・割付・実行STはB版と同一。','']
catalog+=['【標準データ型の意味】（組込み型の定義自体は変更しません）']+[f'{k}：{v}' for k,v in builtin.items()]+['']
for label,cmts,rows in [('グローバル変数',comments,{r['N']:r for r in fields(ng)}),('OtherDeviceローカル・外部参照',local_comments,{r['N']:r for r in fields(nl)})]:
 catalog.append('【'+label+'】')
 for name,c in cmts.items():
  r=rows[name];catalog.extend([f'{name} ／ {r["D"]} ／ {r["G"]}',c])
  if 'AT' in r:catalog.append('割付：'+r['AT'])
  if name in elements and label=='グローバル変数':catalog.extend(f'  {key}：{desc}' for key,desc in elements[name].items())
  catalog.append('')
catalog.append('【構造体データ型とメンバー】')
for name,cms in alltypecomments.items():
 for member,c in cms.items():catalog.extend([name if name==member else name+'.'+member,c,''])
catalogtext='\n'.join(catalog)
element_count=sum(len(v) for v in elements.values())
report={'原本B版':str(SOURCE),'作成C版':str(DEST),'原本SHA256':sha(source),'出力SHA256':sha(data),'原本不変':True,
 '対象':'前回のRCON2台11軸プログラム関連。無関係な既存機器の変数には意味を推測して付記しない',
 'グローバルコメント数':len(comments),'内訳':{'RCON1_RCON2関連':270,'実割付I_O':256,'旧未割付E005候補':144},
 'ローカル・外部参照コメント数':len(local_comments),'ローカル内訳':{'作業変数':12,'既存ダミーマーカー':1,'外部参照':280},
 '構造体型コメント数':4,'構造体メンバーコメント数':39,'配列数':len(elements),'配列要素コメント数':element_count,
 '配列コメント':'26配列の全要素をグローバルに登録。対応するVAR_EXTERNALにも同じ説明を登録',
 '宣言数・名前・データ型・配列範囲・初期値・AT・区分・型メンバー順':'全てB版と同一',
 'ラダー・ST6ブロック・EtherCAT構成・HMI・タスク・コンパイル済み情報':'全てバイト単位同一',
 '変更エントリ':list(updates),'変更エントリ数':len(updates),'不変エントリ数':len(original)-len(updates),'ZIP_CRC':'正常',
 'Sysmac読込み・全体再ビルド':'未実施。B版と同様に使用前の全体再ビルドが必要','実機接続・転送':'未実施',
 '未実装の運転処理':'B版と同じ。通信正常生成・機械安全停止・開始受付の運転シーケンスは未追加',
 '一覧TXT':str(CATALOG),'追加説明TXT':str(SUMMARY)}
summary=f'''RCONコメント追加版／20261019C
保存先：{DEST}

先ほどのB版を残し、コメントだけを追加・整理したC版です。
対象はRCON1の6軸・RCON2の5軸に関する変数・構造体・各メンバーです。
無関係な画像検査・GT2・HMI等の既存変数へ、意味を推測してコメントを追加したものではありません。

【追加・整理したコメント】
グローバル：{len(comments)}変数（RCON関連270、実I/O256、旧未割付候補144）
ローカル/外部参照：{len(local_comments)}件（作業12、既存ダミー1、外部参照280）
構造体：4型・39メンバー
配列：{len(elements)}配列・{element_count}要素。外部参照にも同じ説明を登録。

【Sysmacでの確認場所】
グローバル変数：RCON1_、RCON2_、E001_、E005_で検索し、コメント列を確認します。
ローカル変数：OtherDevice_外部機器の変数テーブル。Conv始まりは計算用、VAR_EXTERNALはグローバルへの参照です。
データ型：ST_RCON_Direct_OUT_Control／IN_Status／OUT_Axis／IN_Axisを開き、型コメントとメンバーコメントを確認します。
配列：変数を展開すると[1]は1軸目/実機No.0などの要素コメントを確認できます。
標準型BOOL・UINT・WORD・DINT・LREAL等の定義そのものは変更せず、コメントと一覧TXTで意味を説明しています。

【説明に含めたこと】
PLCから見たIN/OUT、入力/設定/内部計算/診断の区別、mm・mm/s・G・%・mAの単位。
1軸目[1]と実機軸No.0の違い、ワード番号、制御/状態のbit番号・略号。
確認/許可BOOLのTRUE・FALSEの意味、初期FALSE、前出力保持は停止ではないこと。
旧RCON*_Axis...Rawと末尾_1なしE005候補は、未割付・今回STで不使用と明記しました。
用途未確認の余剰I/Oや構成依存の電源状態は、内容を断定せず未確認と記載しました。

【変更しなかったこと】
名前・型・配列範囲・初期値・保持区分・AT/I/O割付・構造体の構成/順序はB版と同じです。
ST6ブロックを含む実行コード、EtherCAT設定、タスク、HMIはバイト単位で同じです。
動作開始や停止の機能を今回追加したわけではありません。

【使用前の注意】
Sysmacでの読込み・全体再ビルド・実機確認は未実施です。実機へそのまま転送しないでください。
B版の運転上の制限はそのままです。通信正常判定・安全/運転許可・異常停止・DSTR/PEND受付手順は別途設計が必要です。
書込み許可OFFは出力更新保留であり、前のStart/ServoOn等が残り得ます。停止の代わりにしないでください。

全コメント一覧：{CATALOG}
検証記録：{REPORT}
'''
with DEST.open('xb') as f:f.write(data)
with SUMMARY.open('x',encoding='utf-8-sig') as f:f.write(summary)
with CATALOG.open('x',encoding='utf-8-sig') as f:f.write(catalogtext)
with REPORT.open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
assert sha(SOURCE.read_bytes())==sha(source)
assert sha(DEST.read_bytes())==sha(data)
assert CATALOG.read_text(encoding='utf-8-sig')==catalogtext
print(json.dumps(report,ensure_ascii=False,indent=2))
