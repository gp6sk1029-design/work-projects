"""既存ラダー内のインラインST形式を踏襲し、RCON2台の変換処理を別名保存する。"""
from pathlib import Path
import collections,copy,csv,datetime,hashlib,io,json,re,sys,uuid,zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

sys.stdout.reconfigure(encoding='utf8')
HERE=Path(__file__).parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261019A.smc2')
DEST=SOURCE.with_name(SOURCE.stem[:-1]+'B.smc2')
CANDIDATE=HERE/'検証用_v4_20261019B.smc2'
PRIOR=SOURCE.parent/'3089-2603A 検査箱詰め装置(CORE SUB)'/'資料'/'RCON1_6軸_ST変換案_20261017A'
DESIGN=json.loads((HERE.parent/'rcon-bible-20261017'/'manifest.json').read_text(encoding='utf8'))
LADDER_ID='7b1666c7-ee97-4210-81b2-fed5a6172074'
LOCAL_ID='a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10'
GLOBAL_ID='f07dd06c-505c-431b-b9fc-098949805b4e'
TYPE_ID='4bdcdc10-734d-4589-b299-075e93db9b10'
sha=lambda b:hashlib.sha256(b).hexdigest()
def decode(b):return b.decode('utf-8-sig')
def encode_like(b,t):return (b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf8')
def fields(t):
 return [dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in t.splitlines() if l.startswith('++D=')]
def tsv(name):
 with (PRIOR/name).open(encoding='utf8',newline='') as f:return list(csv.reader(f,delimiter='\t'))[1:]
def raw(u,d,n):
 return f'E{1 if u==1 else 5:03d}_{"Out" if d=="OUT" else "In"}_{d}{n:02d}_{"2003" if d=="OUT" else "2004"}_{n+1:02X}'+('' if u==1 else '_1')
def normalized(t):return t.replace('\r\n','\n').replace('\r','\n')
def comment(*lines):return '\n'.join('// '+l for l in lines)+'\n'

source=SOURCE.read_bytes()
with zipfile.ZipFile(io.BytesIO(source)) as z:
 assert z.testzip() is None
 original={n:z.read(n) for n in z.namelist()}; infos=z.infolist(); zipcomment=z.comment
oempath=next(n for n in original if n.endswith('.oem'))
manifestpath=next(n for n in original if n.endswith('.manifest'))
prefix=oempath.rsplit('/',1)[0]+'/'
path=lambda id:prefix+id+'.xml'
oemtext=decode(original[oempath]); root=ET.fromstring(oemtext)
laddertext=decode(original[path(LADDER_ID)]); localtext=decode(original[path(LOCAL_ID)])
globaltext=decode(original[path(GLOBAL_ID)])
assert len([l for l in laddertext.splitlines() if l.strip()])==1,'RCONセクションが想定と異なるため停止'
assert json.loads(laddertext.strip())=={'CLs':[{'__type':'LD','Var':'P_Off'},{'__type':'ST','Ix':1,'Var':'IAI_M','X':1}],'LRI':2,'RRI':3,'VLs':[]}
existing=fields(globaltext); byname={r['N']:r for r in existing}
assert len(existing)==len(byname)
types={e.get('Name'):e for e in ET.fromstring(decode(original[path(TYPE_ID)])).find('DataType')}
for definition in DESIGN['defs']:
 e=types[definition['name']]
 assert [(m.get('Name'),m.get('BaseType')) for m in e]==[(m['name'],m['type']) for m in definition['members']]
for u,axes,words,node in [(1,6,72,1),(2,5,56,5)]:
 for d in ('OUT','IN'):
  for n in range(words):
   r=byname[raw(u,d,n)]
   port=f'{"Out" if d=="OUT" else "In"}_{d}{n:02d}_{"2003" if d=="OUT" else "2004"}_{n+1:02X}'
   assert r['D']=='UINT' and r['AT']==f'ECAT://node#{node}/{port}',r
  assert byname[f'RCON{u}_{d}']['D']==f'ARRAY[1..{axes}] OF ST_RCON_Direct_{d}_Axis'
 assert byname[f'RCON{u}_SpeedUnit_mm_s']['D']=='LREAL'

# 生I/Oの既存書込みがないことをラダーの実行ソースから確認する。
physical={raw(u,d,n) for u,w in [(1,72),(2,56)] for d in ('OUT','IN') for n in range(w)}
for name,b in original.items():
 try:t=decode(b)
 except UnicodeError:continue
 if t.lstrip().startswith('{') and name!=path(LADDER_ID):
  hits=set(re.findall(r'\b(?:E001_|E005_)\w+',t))&physical
  assert not hits,(name,hits)

newglobals=[]
for u,axes,words in [(1,6,72),(2,5,56)]:
 for name,dtype,cmt in tsv('追加グローバル変数.tsv'):
  name=name.replace('RCON1_',f'RCON{u}_')
  # Rxの置換結果[0..55]をTx用の置換へ再投入しない。受信容量と送信使用範囲は別物。
  if '[0..71]' in dtype:dtype=dtype.replace('[0..71]',f'[0..{words-1}]')
  elif '[0..55]' in dtype:dtype=dtype.replace('[0..55]',f'[0..{7+8*axes}]')
  else:dtype=dtype.replace('[1..6]',f'[1..{axes}]')
  cmt=cmt.replace('E001', 'E001' if u==1 else 'E005（末尾_1）').replace('全6軸',f'全{axes}軸').replace('No.0～5',f'No.0～{axes-1}')
  assert name not in byname,name
  newglobals.append({'N':name,'D':dtype,'G':'VAR_GLOBAL','Com':f'RCON{u}：'+cmt})
assert len(newglobals)==56
for u,axes,words in [(1,6,72),(2,5,56)]:
 table={x['N']:x['D'] for x in newglobals}
 assert table[f'RCON{u}_RxRaw']==f'ARRAY[0..{words-1}] OF UINT'
 assert table[f'RCON{u}_RxWord']==f'ARRAY[0..{words-1}] OF WORD'
 assert table[f'RCON{u}_TxWord']==f'ARRAY[0..{7+axes*8}] OF WORD'
 assert table[f'RCON{u}_TxUInt']==f'ARRAY[0..{7+axes*8}] OF UINT'
newlocals=[{'N':n,'D':d,'G':'VAR','Com':c+'（2台を順番に処理する作業用。運転指令は入れない）'} for n,d,c in tsv('追加ローカル変数.tsv')]
assert len(newlocals)==12

blocks=[]
for u,axes,words in [(1,6,72),(2,5,56)]:
 p=f'RCON{u}'; node=1 if u==1 else 5; end=7+8*axes
 header=comment(
  f'【RCON{u}／Node{node}／{axes}軸】直接数値指定の通信変換。加速と減速は共通値です。',
  '前提：全軸が直接数値指定、直動軸、共通8ワード＋軸番号順に各8ワード。実機の設定は別途照合。',
  'OUTはPLC→RCONの指令、INはRCON→PLCの現在値・状態。名前はPLCから見た方向です。',
  '構造体は人が扱いやすい箱、Eで始まる変数はI/Oマップに割付済みの通信の出入口です。',
  'このSTは変換と許可付き代入までです。自動運転、通信正常判定、安全停止、開始受付の管理は含みません。',
  'Sysmacでの全体再ビルドと実機照合は未実施です。このファイルだけで実機へ転送しないでください。')
 original_in=normalized((PRIOR/'01_IN読込と復元.st').read_text(encoding='utf8'))
 start=original_in.index('// 取説の論理ワードへ正規化。')
 logic=original_in[start:].replace('RCON1_',p+'_').replace('INT#71',f'INT#{words-1}').replace('INT#6 DO',f'INT#{axes} DO')
 logic=logic.replace('この提案で決めた','今回の内部設計で決めた')
 logic=logic.replace('// 共通固定領域。',comment('【①-2 共通状態】IN00はユニット全体、IN01は各軸のリンク情報です。',
  'TestABit(ワード, bit番号)は、そのスイッチがONかをBOOLで取り出す命令です。',
  '例：IN01のb0は軸No.0→配列[1]、b1は軸No.1→配列[2]。配列番号と実機軸番号は1違います。')+'// 共通固定領域。')
 logic=logic.replace('FOR ConvAxisIndex',comment('【①-3 軸ごとに同じ読取りを繰り返す】',
  f'FORは1～{axes}軸を順番に処理します。ConvBaseはその軸の先頭番号です。',
  '計算：8+(軸番号-1)×8。1軸目=8、2軸目=16、3軸目=24。先頭8ワードは共通領域です。')+'FOR ConvAxisIndex',1)
 logic=logic.replace('    // 現在位置：',comment('例：下位2540／上位0なら32bit値2540→25.40mm。',
  '上位を16bit左に動かして下位とORで重ねます。SHLが左シフト、ORがビットの合成です。',
  '負位置はDWORD_TO_DINTで符号を復元。下位62996／上位65535なら-2540→-25.40mm。')+'    // 現在位置：')
 logic=logic.replace('    // 状態ワード：',comment('例：Status.ServoReady=TRUEは「サーボON状態を受信した」という意味。',
  'OUT側Control.ServoOn=TRUEは「サーボONを要求する」という意味で、指令と結果を区別します。')+'    // 状態ワード：')
 rx=header+comment('【① 入力を読む → 単位を戻す → 構造体INへ入れる】',
  f'まず{words}個のUINTをRxRawへコピーします。ここでは実入力変数へ一切代入しません。',
  f'軸データはIN08～{end:02d}。IN{end+1:02d}～{words-1:02d}は読みますが、用途を勝手に決めません。',
  'RxRawは通信のまま、RxWordは必要なら上下バイトを入れ替えた後の値です。',
  '注意：確認前も数値・状態は仮に復元します。DataValid=FALSEの値で機械を動かさないでください。')
 rx+='\n'.join(f'{p}_RxRaw[{n}] := {raw(u,"IN",n)};' for n in range(words))+'\n\n'+logic
 original_out=normalized((PRIOR/'02_OUT変換と制御組立.st').read_text(encoding='utf8'))
 outlogic=original_out[original_out.index('ConvUnitOK :='):].replace('RCON1_',p+'_').replace('INT#6 DO',f'INT#{axes} DO').replace('INT#55 DO',f'INT#{end} DO')
 outlogic=outlogic.replace('    // 目標位置：',comment('【数値例】TargetPos_mm=25.40→×100で2540。下位ワード2540、上位ワード0。',
  '700.25mm→70025なので下位4489、上位1。65536を超えた分が上位に入ります。',
  'DINTは符号付きの数、DWORDは同じ32bitの模様。負数の符号を壊さず分割するために使い分けます。',
  'TRUNCは小数部を捨てます。正数+0.5／負数-0.5を先に行い、四捨五入を明示しています。')+'    // 目標位置：')
 outlogic=outlogic.replace('        // 速度は',comment('速度20mm/s：速度単位1.0なら20、0.1なら200を送信します。',
  '加減速0.20G：×100して20。加速と減速の両方に同じ値を使います。',
  '押付け50%：×255÷100=127.5を切捨てて127。押付けの使用可否・上限は実機仕様で別確認。')+'        // 速度は')
 for m in DESIGN['defs'][0]['members']:
  needle=f'    IF {p}_OUT[ConvAxisIndex].Control.{m["name"]} THEN'
  outlogic=outlogic.replace(needle,comment(f'b{m["bit"]} {m["signal"]}／Control.{m["name"]}：{m["explain"]}')+needle)
 tx=header+comment('【② OUTの入力値を通信データへ翻訳する。まだ実出力には書かない】',
  f'例：{p}_OUT[1].TargetPos_mm に25.40を設定すると、1軸目の25.40mm指令候補を作ります。',
  '位置はmm、速度はmm/s、加減速はG、押付け制限は%。人が扱う単位のまま構造体へ設定します。',
  'TxWordは取説のbit並び、TxUIntは実通信へ渡す候補。③の許可がなければ機械には書込みません。',
  'EncodeError=0は数値変換可能という意味だけです。実際のストローク・速度上限・干渉は別に検査します。',
  'エラー番号：1速度単位、2位置、3位置決め幅、4速度、5加減速、6押付け、7ジョグ両方向。',
  '速度0や幅0を正常運転値と認めたものではありません。実機に適した条件はMotionPermitの作成側で確認。',
  '丸め：位置等は四捨五入、押付け制限のみ小数部を切捨てます。')+'\n'+outlogic
 write=header+comment('【③ 確認・許可がそろったときだけ、実際のI/O出力変数へ書く】',
  '初期状態はWriteEnable／LayoutConfirmed／ByteOrderConfirmed／CommOKがすべてFALSEです。',
  'これらを機械条件の確認なしに一括TRUEにしてはいけません。CommOKとMotionPermitは未作成です。',
  'FALSEのときは出力を更新しないだけ。前のStartやServoOnが残り得ます。停止指令ではありません。',
  '安全停止・異常停止は別の設計です。書込み許可をOFFにすることを非常停止の代わりにしないでください。',
  'このSTだけでは動作開始しません。DSTR保持10ms以上、PEND OFF受付→DSTR OFF→PEND ON完了を管理する処理が必要です。',
  'GwWritten/AxisWrittenは「PLC変数へ代入した」印。通信成功・RCONの受付・移動完了を意味しません。',
  '同じE始まりの出力変数を別のラダー/STから書くと、後から書いた値が優先します。出力担当を重複させないでください。')
 write+=f'\n{p}_GwWritten := FALSE;\nFOR ConvAxisIndex := INT#1 TO INT#{axes} DO\n    {p}_AxisWritten[ConvAxisIndex] := FALSE;\nEND_FOR;\n\n'
 write+=f'IF {p}_WriteEnable AND {p}_LayoutConfirmed AND {p}_ByteOrderConfirmed AND {p}_CommOK THEN\n'
 write+=comment('共通指令はMON/RTEのみ。最初のRUN応答に必要なため、軸DataValidとは別にGwApplyで許可します。')
 write+=f'    IF {p}_GwApply THEN\n        {raw(u,"OUT",0)} := {p}_TxUInt[0];\n        {p}_GwWritten := TRUE;\n    END_IF;\n'
 for a in range(1,axes+1):
  b=8+(a-1)*8
  write+='\n'+comment(f'{a}軸目＝実機軸No.{a-1}。OUT{b:02d}～OUT{b+7:02d}の8ワードをまとめて代入。',
   'AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。',
   '途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。')
  write+=f'    IF {p}_AxisApply[{a}] AND {p}_EncodeOK[{a}] AND {p}_IN[{a}].DataValid\n       AND {p}_MotionPermit[{a}] THEN\n'
  write+='\n'.join(f'        {raw(u,"OUT",n)} := {p}_TxUInt[{n}];' for n in range(b,b+8))+'\n'
  write+=f'        {p}_AxisWritten[{a}] := TRUE;\n    END_IF;\n'
 write+='END_IF;\n'+comment(f'OUT01～07、OUT{end+1:02d}～{words-1:02d}は、このSTからは一切書き換えません。',
  '現在の実機設定・別処理の用途が未確認なので、余剰領域を勝手にゼロクリアしません。')
 for step,(text,title) in enumerate([(rx,'IN読取りと現在値の復元'),(tx,'OUT数値変換と制御bit組立'),(write,'許可条件付きの実I/O書込み')],1):
  blocks.append({'unit':u,'axes':axes,'words':words,'step':step,'title':f'RCON{u}－{step} {title}',
   'text':text,'file':f'RCON{u}_{step:02d}_{title.replace("/","_")}.st'})

# 全参照を実変数表と照合し、必要なVAR_EXTERNALもローカル表に登録する。
allcode='\n'.join(re.sub(r'//[^\n]*','',b['text']) for b in blocks)
references=set(re.findall(r'\b(?:RCON[12]_|E001_|E005_|Conv)\w*',allcode))
globalmap=byname|{x['N']:x for x in newglobals}
localmap={x['N']:x for x in newlocals}
assert references <= set(globalmap)|set(localmap),references-set(globalmap)-set(localmap)
externalnames=references&set(globalmap)
currentlocals=fields(localtext); currentlocalmap={x['N']:x for x in currentlocals}
assert not set(localmap)&set(currentlocalmap)
newexternals=[]
for name in sorted(externalnames):
 if name in currentlocalmap:
  assert currentlocalmap[name]['D']==globalmap[name]['D'] and currentlocalmap[name]['G']=='VAR_EXTERNAL'
 else:
  x=globalmap[name]; newexternals.append({'N':name,'D':x['D'],'G':'VAR_EXTERNAL','Com':x.get('Com','RCON通信I/O。実割付済みのグローバル変数を参照')})
assert len(newexternals)==280,len(newexternals)

# 既存I/Oの名前・型・割付は保持し、コメントだけを意味のある説明に補足する。
iocomments={}
for u,axes,words in [(1,6,72),(2,5,56)]:
 for direction in ['OUT','IN']:
  for n in range(words):
   c=DESIGN['io'][direction][n][1] if n<8+8*axes else f'【{direction}{n:02d}】用途未確認領域。今回の軸データ変換では未使用。'
   iocomments[raw(u,direction,n)]=f'RCON{u}（Node{1 if u==1 else 5}） '+c+('／今回書込まない' if direction=='OUT' and (1<=n<=7 or n>=8+8*axes) else '')
for x in newexternals:
 if x['N'] in iocomments:x['Com']=iocomments[x['N']]
def line(x):return '++D='+x['D']+'\tN='+x['N']+'\tG='+x['G']+'\tCom='+x['Com']+'\r\n'
gout=[]
for oldline in globaltext.splitlines(keepends=True):
 m=re.search(r'(?:^|\t)N=([^\t\r\n]+)',oldline)
 if m and m[1] in iocomments:
  ending=oldline[len(oldline.rstrip('\r\n')):]
  parts=[p for p in oldline.rstrip('\r\n').split('\t') if not p.startswith('Com=')]
  oldline='\t'.join(parts)+'\tCom='+iocomments[m[1]]+ending
 gout.append(oldline)
newglobaltext=''.join(gout)+''.join(line(x) for x in newglobals)
marker='+GN=VAR_EXTERNAL\tGA=External\tGVT=ExternalGroup'
assert localtext.count(marker)==1
newlocaltext=localtext.replace(marker,''.join(line(x) for x in newlocals)+marker,1)+''.join(line(x) for x in newexternals)

# 既存DLEP1_GT2のISTモデルとInlineエンティティ登録をそのまま踏襲する。
sample=next(e for e in root.iter('Entity') if e.get('id')=='76d6fc6a-f4a4-46b3-8891-ff16aa25214c')
section=next(e for e in root.iter('Entity') if e.get('id')==LADDER_ID)
assert not list(e for e in section.iter('Entity') if e.get('type')=='Inline')
children=[]; rungs=[]; bookmark=original[prefix+'76d6fc6a-f4a4-46b3-8891-ff16aa25214c.BookmarkGroup']
modified=datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
addedfiles={}
for b in blocks:
 entity_id=str(uuid.uuid4()); tracking_id=str(uuid.uuid4())
 b['entityId']=entity_id; b['trackingId']=tracking_id
 e=copy.deepcopy(sample); e.tail=None
 e.set('id',entity_id); e.set('name',tracking_id); e.set('trackingId',tracking_id)
 e.set('dateCreated',modified); e.set('dateLastModified',modified)
 ET.indent(e,space='  ',level=13)
 children.append('                          '+ET.tostring(e,encoding='unicode').replace('\n','\r\n')+'\r\n')
 text=b['text'].replace('\n','\r\n')
 rung={'CLs':[{'__type':'IST','EID':tracking_id,'H':520,'TXT':text,'W':1100}],
  'CMT':b['title']+'\r\n'+('読取り専用。DataValidがFALSEの値で運転しない。' if b['step']==1 else '内部計算のみ。実出力への代入は次のST。' if b['step']==2 else '初期は書込みOFF。更新保留は停止ではない。'),
  'LRI':1,'RRI':2,'VLs':[]}
 rungs.append(json.dumps(rung,ensure_ascii=False,separators=(',',':'))+'\r\n')
 addedfiles[prefix+entity_id+'.BookmarkGroup']=bookmark
newladder=laddertext+''.join(rungs)
pos=oemtext.index('id="'+LADDER_ID+'"')
close=oemtext.index('</ChildEntities>',pos)
newoem=oemtext[:close]+''.join(children)+oemtext[close:]
for edited_id in [LADDER_ID,LOCAL_ID,GLOBAL_ID,'0fe7f9c6-eab4-465d-bb5c-054ab06c6003']:
 entity_tag=re.search(r'<Entity\b[^>]*\bid="'+edited_id+r'"[^>]*>',newoem)
 assert entity_tag
 edited_tag=re.sub(r'dateLastModified="[^"]*"','dateLastModified='+quoteattr(modified),entity_tag[0])
 newoem=newoem[:entity_tag.start()]+edited_tag+newoem[entity_tag.end():]
# 追加対象だけ変更し、OEM全体の改行・属性順を再整形しない。
oldname=root.find('Entity').get('name')
assert oldname==SOURCE.stem
tag=re.search(r'<Entity\b[^>]*\btype="Solution"[^>]*>',newoem)
assert tag
newtag=tag[0].replace('name='+quoteattr(oldname),'name='+quoteattr(DEST.stem))
if root.find('Entity').get('DN')==oldname:newtag=newtag.replace('DN='+quoteattr(oldname),'DN='+quoteattr(DEST.stem))
newoem=newoem[:tag.start()]+newtag+newoem[tag.end():]
manifest=decode(original[manifestpath])
assert 'solutionName='+quoteattr(oldname) in manifest
newmanifest=manifest.replace('solutionName='+quoteattr(oldname),'solutionName='+quoteattr(DEST.stem),1)
updates={path(GLOBAL_ID):newglobaltext,path(LOCAL_ID):newlocaltext,path(LADDER_ID):newladder,oempath:newoem,manifestpath:newmanifest}

# 静的検証：既存の変数名・型・AT・グループ・初期値は一切変更しない。
newrows=fields(newglobaltext); before={x['N']:x for x in existing}; after={x['N']:x for x in newrows}
assert len(newrows)==len(after)==len(existing)+56
for name,x in before.items():assert {k:v for k,v in x.items() if k!='Com'}=={k:v for k,v in after[name].items() if k!='Com'}
for x in newglobals:assert 'AT' not in after[x['N']] and after[x['N']]['G']=='VAR_GLOBAL'
locals_after=fields(newlocaltext); lm={x['N']:x for x in locals_after}
assert len(locals_after)==len(lm)==len(currentlocals)+12+len(newexternals)
for x in currentlocals:assert lm[x['N']]==x
for name in externalnames:assert lm[name]['G']=='VAR_EXTERNAL' and lm[name]['D']==after[name]['D']
for x in newlocals:assert lm[x['N']]['G']=='VAR'
rr=ET.fromstring(newoem); ids=[e.get('id') for e in rr.iter('Entity')]
assert len(ids)==len(set(ids))
newsection=next(e for e in rr.iter('Entity') if e.get('id')==LADDER_ID)
inlines=[e for e in newsection.iter('Entity') if e.get('type')=='Inline']
ladderparsed=[json.loads(l) for l in newladder.splitlines() if l.strip()]
assert len(inlines)==6 and len(ladderparsed)==7
assert ladderparsed[0]==json.loads(laddertext.strip())
assert {e.get('name') for e in inlines}=={r['CLs'][0]['EID'] for r in ladderparsed[1:]}
for u,axes,words in [(1,6,72),(2,5,56)]:
 texts=[b['text'] for b in blocks if b['unit']==u]
 code='\n'.join(re.sub(r'//[^\n]*','',t) for t in texts)
 written=re.findall(r'\b(E\d{3}_\w+)\s*:=',code)
 assert len(written)==1+8*axes and set(written)=={raw(u,'OUT',0)}|{raw(u,'OUT',n) for n in range(8,8+8*axes)}
 assert len(re.findall(fr'RCON{u}_RxRaw\[\d+\]\s*:=',code))==words
 for control in DESIGN['defs'][0]['members']:assert '.Control.'+control['name'] in code
 for status in DESIGN['defs'][1]['members']:assert '.Status.'+status['name'] in code
 if u==2:assert not re.search(r'\b(?:RCON1_|E001_)',code)
 else:assert not re.search(r'\b(?:RCON2_|E005_)',code)

buf=io.BytesIO()
with zipfile.ZipFile(buf,'w') as z:
 z.comment=zipcomment
 for info in infos:z.writestr(copy.copy(info),encode_like(original[info.filename],updates[info.filename]) if info.filename in updates else original[info.filename])
 for name,b in addedfiles.items():z.writestr(name,b,compress_type=zipfile.ZIP_DEFLATED)
result=buf.getvalue()
with zipfile.ZipFile(io.BytesIO(result)) as z:
 assert z.testzip() is None
 for n,b in original.items():
  if n not in updates:assert z.read(n)==b,n
 for n,t in updates.items():
  assert decode(z.read(n))==t
  if n in (oempath,manifestpath):ET.fromstring(t)
 assert z.read(path(TYPE_ID))==original[path(TYPE_ID)]
assert SOURCE.read_bytes()==source,'原本が他の操作で更新されたため停止'
assert not CANDIDATE.exists(),'同名検証ファイルが存在'
with CANDIDATE.open('xb') as f:f.write(result)
for b in blocks:(HERE/b['file']).write_text(b['text'],encoding='utf8')
def output_tsv(name,rows):
 with (HERE/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f,delimiter='\t'); w.writerow(['変数名','データ型','区分','コメント']);w.writerows((x['N'],x['D'],x['G'],x.get('Com','')) for x in rows)
output_tsv('追加グローバル56変数.tsv',newglobals)
output_tsv('追加ローカル12変数.tsv',newlocals)
output_tsv('追加外部参照280変数.tsv',newexternals)
with (HERE/'実I_O割付照合256変数.tsv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['変数名','データ型','割付AT','コメント'])
 w.writerows((n,after[n]['D'],after[n]['AT'],after[n]['Com']) for n in iocomments)
report={'原本':str(SOURCE),'保存先':str(DEST),'候補':str(CANDIDATE),'原本SHA256':sha(source),'出力SHA256':sha(result),
 '原本不変':SOURCE.read_bytes()==source,'セクション':'OtherDevice_外部機器 / RCON_IAI','インラインST追加数':6,
 '元の回路保持':True,'グローバル追加':56,'既存グローバル数':len(existing),'更新後グローバル数':len(newrows),'ローカル作業変数追加':12,
 'ローカル外部参照追加':len(newexternals),'既存の型4種類39メンバー': '完全不変・共用',
 '既存変数名・データ型・AT・初期値・区分':'全て保持。既存I/O256個のコメントだけ追加',
 '実I_O宣言照合':256,'追加保持変数':0,'出力代入箇所':90,'未使用出力領域':'Node1 OUT01～07・56～71、Node5 OUT01～07・48～55を書換えない',
 '変更既存エントリ数':len(updates),'変更エントリ':list(updates),'追加エントリ数':len(addedfiles),'既存不変エントリ数':len(original)-len(updates),
 'EtherCAT構成・HMI・他セクション・タスク':'バイト単位不変','初期書込許可':'非保持BOOLの既定FALSE。コードでTRUEを設定しない',
 '起動シーケンス・通信正常生成・機械安全停止':'今回未実装。変換処理とは別工程',
 'Sysmac全体再ビルド':'未実施・必須。既存コンパイル済みデータを引き継いでいる',
 '実機接続・転送':'未実施','blocks':[{k:v for k,v in b.items() if k!='text'} for b in blocks],
 'newGlobals':newglobals,'newLocals':newlocals,'externalNames':sorted(externalnames)}
(HERE/'implementation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ['blocks','newGlobals','newLocals','externalNames']},ensure_ascii=False,indent=2))
