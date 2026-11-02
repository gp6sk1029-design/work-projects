import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile, FileBlob } from '@oai/artifact-tool';

// 既存資料を読取り、新しい学習・登録資料だけを作成する。実機には接続しない。
const folder='C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/資料';
const oldDir=folder+'/RCON_直接数値指定_6軸_IO構造体_20261017A';
const output=folder+'/RCON_直接数値指定_INOUT登録バイブル_20261017B.xlsx';
const previews=new URL('./previews/',import.meta.url);
const old=await SpreadsheetFile.importXlsx(await FileBlob.load(oldDir+'/RCON_直接数値指定_6軸_IOリスト・構造体.xlsx'));
const ref=await fs.readFile(oldDir+'/構造体定義_参考.txt','utf8');
const rename={ST_RCON_DirectControl:'ST_RCON_Direct_OUT_Control',ST_RCON_DirectStatusBits:'ST_RCON_Direct_IN_Status',ST_RCON_DirectCommand:'ST_RCON_Direct_OUT_Axis',ST_RCON_DirectFeedback:'ST_RCON_Direct_IN_Axis'};
const defs=[...ref.matchAll(/TYPE (\w+) :\s*STRUCT([\s\S]*?)END_STRUCT;/g)].filter(m=>rename[m[1]]).map(m=>({old:m[1],name:rename[m[1]],members:[...m[2].matchAll(/(\w+)\s*:\s*(\w+)\s*;\s*\(\* (.*?) \*\)/g)].map(x=>({name:x[1],type:rename[x[2]]??x[2],comment:x[3]}))}));
const controlBits=[0,1,2,3,4,5,6,7,8,10,11,12,13,14,15];
const controlSignals=['DSTR','HOME','STP','RES','SON','JISL','JVEL','JOG-','JOG+','GSL0','GSL1','PUSH','DIR','INC','BKRL'];
const statusBits=[0,1,2,3,4,5,7,8,12,13,14,15];
const statusSignals=['PEND','HEND','MOVE','ALM','SV','PSFL','ALML','MEND','ZONE1','ZONE2','CRDY','EMGS'];
const units={TargetPos_mm:'mm',PositionBand_mm:'mm',Speed_mm_s:'mm/s',AccDec_G:'G',PushLimit_pct:'%',ActualPos_mm:'mm',Current_mA:'mA',ActualSpeed_mm_s:'mm/s',AlarmCode:'コード',DataValid:'内部判定'};
const boolExplain={
 Start:'TRUEで開始要求。受付応答と10ms以上の保持を確認してOFF。常時ONにしない。',
 Home:'TRUEで原点復帰を指令。原点復帰完了はIN側HomeDoneで確認。',
 Pause:'TRUEで一時停止、FALSEで解除。非常停止・安全停止の代用ではない。',
 Reset:'TRUEでアラームリセット要求。コールドスタート級の異常には使用できない。',
 ServoOn:'TRUEでサーボON要求。ON状態はIN側ServoReadyで確認。',
 InchingSelect:'TRUEは一定距離のインチング、FALSEは押している間のジョグ。',
 JogSpeedSelect:'FALSEは速度No.26・距離No.48、TRUEは速度No.47または指令速度・距離No.49。',
 JogMinus:'TRUEで原点方向へジョグ。反対方向指令との同時ONを防ぐ。',
 JogPlus:'TRUEで反原点方向へジョグ。反対方向指令との同時ONを防ぐ。',
 GainSelect0:'GainSelect1と組合せてサーボゲインセット0～3を選ぶ。機械調整用。',
 GainSelect1:'GainSelect0との2bitで選択。速度指令とは別の機能。',
 PushEnable:'TRUEは押付け、FALSEは通常位置決め。押付け条件は別途確認。',
 PushDirection:'CON方式押付け時、TRUEは反原点方向、FALSEは原点方向。',
 RelativeMove:'FALSEは絶対座標、TRUEは現在位置からの相対移動量。',
 BrakeRelease:'TRUEはブレーキ強制解除。通常FALSE。縦軸では落下等の危険がある。',
 PositionDone:'TRUEは位置決め完了。今回の指令受付・完了の順序と合わせて確認する。',
 HomeDone:'TRUEは原点復帰が完了し原点情報を維持している状態。',
 Moving:'TRUEは移動中。FALSEだけで目的地到着とは判断しない。',
 Alarm:'TRUEはアラーム発生中。AlarmCodeも読み原因を確認する。',
 ServoReady:'TRUEはサーボON状態。OUT側のServoOn指令と区別する。',
 PushMiss:'TRUEは押付け空振り完了。押付け成功と同一視しない。',
 OverloadWarning:'TRUEは過負荷警告またはメッセージレベルのアラーム。',
 CommandDone:'TRUEは位置決め・押付け・空振りのいずれかで完了。成功保証ではない。',
 Zone1:'TRUEは現在位置がゾーン1の設定範囲内。',Zone2:'TRUEは現在位置がゾーン2の設定範囲内。',
 ControllerReady:'TRUEはコントローラー準備完了。通信・安全等の条件は別途確認。',
 EmergencyStop:'TRUEは非常停止状態のモニター。安全回路の代用にはしない。'
};
for(let i=0;i<defs.length;i++){
 defs[i].order=i+1;
 defs[i].dir=i===0||i===2?'OUT':'IN';
 for(let j=0;j<defs[i].members.length;j++){
  const m=defs[i].members[j];
  if(i<2){m.bit=(i===0?controlBits:statusBits)[j];m.signal=(i===0?controlSignals:statusSignals)[j];m.explain=boolExplain[m.name];}
 }
}
const io={};
for(const dir of ['OUT','IN']){
 io[dir]=old.worksheets.getItem(dir+'_IO').getRange('A2:I57').values.map(r=>{
  const x=[...r];x[0]=r[0].replace('RCON1_Dir_',`RCON1_${dir}_`);
  x[6]=r[6].replace(/RCON1_DirectAxis\[(\d)\]\.Cmd/g,'RCON1_OUT[$1]').replace(/RCON1_DirectAxis\[(\d)\]\.Fbk/g,'RCON1_IN[$1]');
  x[1]=`${dir==='OUT'?'PLC→RCON':'RCON→PLC'} ${r[1]}`;
  if(dir==='OUT'&&x[4]==='DINT（結合後）')x[4]='DINT（分割前）';
  return x;
 });
}
const wb=Workbook.create();
const palette={ink:'#20354B',header:'#223B54',out:'#265FA0',outFill:'#EAF2FC',input:'#19766C',inFill:'#E9F5F1',amber:'#FFF2CC',muted:'#637589'};
function col(i){let s='';for(i++;i;i=Math.floor((i-1)/26))s=String.fromCharCode(65+(i-1)%26)+s;return s;}
function base(name,widths,rows=70){
 const s=wb.worksheets.add(name);s.showGridLines=false;
 const range=s.getRange(`A1:${col(widths.length-1)}${rows}`);
 range.format.font={name:'Arial',size:11,color:palette.ink};range.format.verticalAlignment='center';range.format.rowHeight=28;
 widths.forEach((w,i)=>s.getRange(`${col(i)}1:${col(i)}${rows}`).format.columnWidth=w);
 return s;
}
function title(s,text,last='F',note=''){
 s.getRange('A2').values=[[text]];s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:palette.header};s.getRange(`A2:${last}2`).format.rowHeight=32;
 s.getRange(`A3:${last}3`).format.borders={bottom:{style:'thin',color:'#9FB0C2'}};
 if(note){s.getRange('A4').values=[[note]];s.getRange(`A4:${last}4`).format.rowHeight=27;}
}
function table(s,row,headers,data,{height=48,color=palette.header,wrap=true}={}){
 const end=row+data.length,last=col(headers.length-1);
 s.getRange(`A${row}:${last}${end}`).values=[headers,...data];
 s.getRange(`A${row}:${last}${row}`).format={fill:color,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
 if(data.length){s.getRange(`A${row+1}:${last}${end}`).format.rowHeight=height;s.getRange(`A${row+1}:${last}${end}`).format.wrapText=wrap;
  for(let r=row+1;r<=end;r++)if((r-row)%2===0)s.getRange(`A${r}:${last}${r}`).format.fill='#F4F7FA';
 }
 s.getRange(`A${row}:${last}${end}`).format.borders={bottom:{style:'thin',color:'#C9D4DF'}};
 return end;
}

// 登録ガイド：型（設計図）と変数（実体）を分けて案内する。
const guide=base('登録ガイド',[13,43,54,58],54);guide.tabColor=palette.header;
title(guide,'RCON 直接数値指定 IN・OUT登録ガイド','D','6軸／通常EtherCAT／直動軸。2026-10-17作成。実機・既存資料は変更していません。');
table(guide,6,['方向','意味','プログラム用の変数','通信との関係'],[
 ['OUT','PLCからRCONへ送る指令','RCON1_OUT[1..6]','mm等の内部値をUINTへ変換して送る'],
 ['IN','RCONからPLCへ受け取る情報','RCON1_IN[1..6]','受信UINTをmm等の内部値へ復元する']
],{height:46});guide.getRange('A7:D7').format.fill=palette.outFill;guide.getRange('A8:D8').format.fill=palette.inFill;
table(guide,11,['登録順','作成するデータ型名','内容','参照するタブ'],defs.map(d=>[d.order,d.name,d.order===1?'出力指令15個のBOOL':d.order===2?'入力状態12個のBOOL':d.dir==='OUT'?'目標位置等5項目＋Control':'現在値等4項目＋Status＋DataValid',d.dir==='OUT'?'OUT型・メンバー':'IN型・メンバー']),{height:44});
table(guide,18,['登録順','グローバル変数名','データ型欄に入力する内容','コメント・設定'],[
 [5,'RCON1_OUT','ARRAY[1..6] OF ST_RCON_Direct_OUT_Axis','RCON1へ送る6軸分の指令。非保持。起動BOOLを保持しない。'],
 [6,'RCON1_IN','ARRAY[1..6] OF ST_RCON_Direct_IN_Axis','RCON1から受けた6軸分の情報。非保持。DataValid初期FALSE。'],
 [7,'RCON1_SpeedUnit_mm_s','LREAL','速度の1カウント量。実機設定の1.0か0.1を確認。0や不明のまま使わない。']
],{height:58});
table(guide,24,['項目','値','意味','条件'],[
 ['軸数',6,'軸','RCON軸No.0～5の順'],['固定領域',8,'ワード／方向','ゲートウェイ・リンク・電源等'],['1軸',8,'ワード／方向','直接数値指定モード'],['合計',null,'ワード／方向','固定＋軸数×1軸'],['通信容量',null,'Byte／方向','全6軸同モード、追加占有なし'],['ESI','112Byte/112Byte','RCGW-ECT(112Byte/112Byte)','64Byteのままでは全6軸直接数値指定を収容できない']
],{height:38});guide.getRange('B28').formulas=[['=B26+B25*B27']];guide.getRange('B29').formulas=[['=B28*2']];
table(guide,33,['人の呼び方','RCON軸No.','OUT／INポート範囲','内部変数の要素'],Array.from({length:6},(_,i)=>[`${i+1}軸目`,i,`${8+8*i}～${15+8*i}`,`RCON1_OUT[${i+1}] ／ RCON1_IN[${i+1}]`]),{height:32});
table(guide,42,['順番','読むタブ','わかること','注意'],[
 [1,'OUT型・メンバー／IN型・メンバー','構造体ごとにメンバー名・型・コメントを登録','ST_は今回の命名。メーカーが自動で作る名前ではない'],
 [2,'組合せ例・型選び','型と変数と配列を組み合わせた指定方法','本資料のARRAY[1..6]は人の軸番号。実機No.は0始まり'],
 [3,'OUT_IO／IN_IO','Raw変数をI/Oマップへ登録する一覧','A2:B57のみがコピー範囲。構造体全体をPDOへ割付しない'],
 [4,'解説_取説から設計','取説の事実から型を決めるプロセス','メーカー仕様とPLC内部の設計判断を区別する'],
 [5,'解説_単位と上下ワード','入力変更で分割・結合・符号・単位を学習','Excelの計算例。実機に書き込む値や運転推奨値ではない'],
 [6,'解説_登録と動作確認','登録から試験までの進め方','変換・起動プログラムは本資料に実装していない']
],{height:55});

// 登録表：A～C列はメンバー名・データ型・日本語コメント。
const blockRows={};
for(const dir of ['OUT','IN']){
 const s=base(dir+'型・メンバー',[27,40,64,18,25,55],43);s.tabColor=dir==='OUT'?palette.out:palette.input;
 title(s,`${dir} 構造体・メンバー登録一覧`,'F',`${dir==='OUT'?'PLC→RCONの出力指令':'RCON→PLCの入力情報'}。A～C列は登録用。通信UINTへの変換は別途必要です。`);
 let row=6;
 for(const d of defs.filter(d=>d.dir===dir)){
  s.getRange(`A${row}`).values=[[`登録順${d.order}：${d.name}`]];s.getRange(`A${row}:F${row}`).format.fill=dir==='OUT'?palette.outFill:palette.inFill;s.getRange(`A${row}:F${row}`).format.rowHeight=30;
  const r=row+2;blockRows[d.name]={sheet:s.name,start:r+1,end:r+d.members.length};
  const data=d.members.map(m=>{
   let relation='',evidence='',comment=m.explain??m.comment;
   if(m.bit!==undefined){relation=`論理b${m.bit}／${m.signal}`;evidence=dir==='OUT'?'MJ0384 6-33':m.bit>=6?'MJ0384 6-34':'MJ0384 6-35';}
   else if(m.name==='DataValid'){relation='PLC内部で算出';evidence='今回の設計。直接の受信bitではない';}
   else if(m.name==='Control'||m.name==='Status'){relation='子の構造体';evidence='今回のまとめ方。論理bitは取説参照';}
   else {relation=dir==='OUT'?'送信前に整数化':'受信後に復元';evidence=dir==='OUT'?'MJ0384 6-30／6-32':'MJ0384 6-31／6-34';}
   return [m.name,m.type,comment,units[m.name]??(m.type==='BOOL'?'ON/OFF':'構造体'),relation,evidence];
  });
  const end=table(s,r,['メンバー名','データ型','日本語コメント','単位','通信との対応','根拠・位置付け'],data,{height:d.order<=2?59:64,color:dir==='OUT'?palette.out:palette.input});
  s.getRange(`A${r+1}:C${end}`).format.fill=dir==='OUT'?palette.outFill:palette.inFill;
  row=end+3;
 }
 s.freezePanes.freezeRows(4);
}

const combinations=base('組合せ例・型選び',[27,68,41,63],55);
title(combinations,'型と変数を組み合わせて使う','D','型＝入れ物の設計図、変数＝実際の入れ物、メンバー＝中身、配列＝同じ入れ物を6個並べること。');
table(combinations,6,['場面','指定する変数の全文','最終的な型','意味・注意'],[
 ['1軸の目標位置','RCON1_OUT[1].TargetPos_mm','LREAL','1軸目に指定する位置mm。絶対／相対はRelativeMoveで決まる。'],
 ['2軸の速度','RCON1_OUT[2].Speed_mm_s','LREAL','2軸目の速度mm/s。通信時は実機単位で整数化する。'],
 ['1軸の開始指令','RCON1_OUT[1].Control.Start','BOOL','OUT配列の1軸、その中のControl、その中のStart。DSTRへ変換。'],
 ['1軸のサーボON要求','RCON1_OUT[1].Control.ServoOn','BOOL','PLCから出す要求。実際にONになったかはIN側で読む。'],
 ['1軸のサーボON状態','RCON1_IN[1].Status.ServoReady','BOOL','RCONから返るSV。要求と状態を同じ変数にしない。'],
 ['6軸の現在位置','RCON1_IN[6].ActualPos_mm','LREAL','6軸目（実機No.5）の現在位置。受信2ワードから復元する。'],
 ['6軸の異常','RCON1_IN[6].Status.Alarm','BOOL','異常の有無。内容は同じ軸のAlarmCodeを見る。'],
 ['1軸の完了','RCON1_IN[1].Status.PositionDone','BOOL','PENDの状態。今回の指令受付後の再ONかを確認する。'],
 ['データ有効性','RCON1_IN[1].DataValid','BOOL','通信・軸リンク・割付等からPLCで算出。単一PDOには対応しない。']
],{height:52});
table(combinations,18,['階層','1軸目の開始指令の読み方','データ型','説明'],[
 ['全体','RCON1_OUT','ARRAY[1..6] OF ST_RCON_Direct_OUT_Axis','出力用の軸構造体を6個並べた変数'],
 ['軸を選ぶ','RCON1_OUT[1]','ST_RCON_Direct_OUT_Axis','そのうち1軸目の入れ物'],
 ['制御群を選ぶ','RCON1_OUT[1].Control','ST_RCON_Direct_OUT_Control','1軸目の起動・原点等の指令群'],
 ['指令を選ぶ','RCON1_OUT[1].Control.Start','BOOL','最終的にON/OFFを持つ1つの指令']
],{height:48});
table(combinations,25,['データ型','表現できる値','今回の用途','選び方'],[
 ['BOOL','FALSE／TRUE','Control・Statusの各bit','1つのON/OFFを表す。構造体順番は通信bit順の保証ではない。'],
 ['UINT','0～65535／16bit整数','ESIに示されたI/Oマップの各Rawポート','通信容器。上下ワードの片方だけを位置mmと解釈しない。'],
 ['WORD','16bitのビット列','制御／状態ワードを組立・分解する中間型','数値ではなくbit集合として扱うとき。I/Oポート型はUINTのまま。'],
 ['INT','-32768～32767／16bit符号付き','現在速度Rawの解釈','マイナス方向の2の補数を符号付きとして読む。'],
 ['DINT','-2147483648～2147483647／32bit符号付き','目標位置・現在位置・現在電流の復元','符号付き32bitという取説の指定に合わせる。'],
 ['UDINT','0～4294967295／32bit符号なし','非負の位置決め幅を扱う内部推奨型','今回の選定。メーカーの符号なし保証を意味しない。'],
 ['DWORD','32bitのビット列','2ワードを結合・分割する中間型','負数を含めビット表現を保持する。数値変換と混同しない。'],
 ['LREAL','小数を扱える64bit浮動小数点','mm・mm/s・G・%の内部指令と表示','人が扱いやすい単位用に今回選定。通信は整数のため換算が必要。'],
 ['構造体型','異なる型のメンバーを1つにまとめる','OUT_Axis／IN_Axis／Control／Status','メーカー固定レイアウトではなく、使いやすさのための内部設計。'],
 ['ARRAY[1..6] OF 型名','同じ型を要素1～6に並べる','6軸分のRCON1_OUT／RCON1_IN','6種類の型を作るのではない。同じ型を6軸で使い回す。']
],{height:58});
table(combinations,38,['旧資料の名前','今回の名前','変更内容','登録時の注意'],[
 ['ST_RCON_DirectControl','ST_RCON_Direct_OUT_Control','方向を明記','旧型を自動置換する機能はない。既存参照を確認する。'],
 ['ST_RCON_DirectStatusBits','ST_RCON_Direct_IN_Status','方向を明記','既存のプロジェクトを無条件に上書きしない。'],
 ['ST_RCON_DirectCommand','ST_RCON_Direct_OUT_Axis','1軸の出力用と明記','メンバーは既存の5数値＋Controlを維持。'],
 ['ST_RCON_DirectFeedback','ST_RCON_Direct_IN_Axis','1軸の入力用と明記','4取得値＋Status＋DataValidを維持。'],
 ['RCON1_DirectAxis[n].Cmd','RCON1_OUT[n]','Cmd/Fbkの親階層を省略','旧ST_RCON_DirectAxis型は新規案では使用しない。'],
 ['RCON1_DirectAxis[n].Fbk','RCON1_IN[n]','IN/OUTの別配列へ分離','型名変更だけでは既存ラダー・変換は変更されない。']
],{height:52});

for(const dir of ['OUT','IN']){
 const s=base(dir+'_IO',[48,79,12,12,27,13,53,29,19],61);
 table(s,1,['変数名（コピー）','変数コメント（コピー）','ポート','I/O型','変換・解釈型','軸No.','内部構造体への対応','通信単位','Index:SubIndex'],io[dir],{height:48,color:dir==='OUT'?palette.out:palette.input});
 s.getRange('A2:B57').format.fill=dir==='OUT'?palette.outFill:palette.inFill;s.tabColor=dir==='OUT'?palette.out:palette.input;s.freezePanes.freezeRows(1);
 s.getRange('A59').values=[['コピー範囲：A2:B57。112Byte版の先頭ポートへ、順序・既存割付を照合してから登録。C列以降・見出しはコピーしない。']];
 s.getRange('A60').values=[['Rawは全112ポートUINT。内部構造体を直接I/Oマップへ割付しない。通信型が同じでも内容・単位は異なります。']];
}

const process=base('解説_取説から設計',[13,29,57,58,50,31],58);process.tabColor='#6C668C';
title(process,'取説から構造体を設計するプロセス','F','「取説に書いてあること」と「PLCを使いやすくするために今回決めたこと」を分けて読む。');
table(process,6,['手順','確認する場所','取説・ESIから読み取る事実','今回の設計への変換','なぜそうするか','仕様か設計か'],[
 [1,'MJ0384 6-1／6-3','固定8ワードと、直接数値指定1軸8ワード。モードで内容が変わる。','全6軸で8＋8×6＝56ワード＝112Byte／方向。','まず必要容量とモードを決めないと、ポートの意味がずれる。','容量は仕様。6軸同モードは今回の前提。'],
 [2,'MJ0384 6-30／6-31','PLC出力は指令、PLC入力は現在値・状態。','OUT用とIN用の構造体・配列を別々に作る。','送る値と受ける値を同じ変数にせず、方向を見分ける。','方向は仕様。分け方と名前は設計。'],
 [3,'公式ESIの112Byte機器','OUT00～55／IN00～55、2003／2004、各ポート16bitのUINT。','I/OマップのRaw変数は全てUINTで登録する。','ESIは通信の容器の型を指定する。mmなどの意味までは示さない。','UINT／ポート数はESI仕様。Raw名は設計。'],
 [4,'MJ0384 6-3／6-30','目標位置は下位・上位の2ワード。固定8ワードの後に軸データ。','1軸目OUT08/09をTargetPosLoRaw／HiRawとする。','32bitを2つの16bit通信容器に分けて送る。','順序は仕様。実機のワード・バイト順を照合。'],
 [5,'MJ0384 6-32 位置データ','32bit符号付き、直動軸0.01mm単位。負数は2の補数。','通信値はDINTで扱い、内部TargetPos_mmはLREALにする。','負位置を維持しつつ、人は25.40mmのように入力できる。','DINTの意味は仕様に対応。LREALと名前は設計。'],
 [6,'MJ0384 6-32 位置決め幅','32bit整数、0.01mm単位。初期値の自動適用はない。','PositionBand_mmはLREAL。非負の内部整数としてUDINTを推奨。','幅をmmで入力し、送信前に範囲検査と整数化を行う。','32bitと単位は仕様。UDINTは内部の推奨型。'],
 [7,'MJ0384 6-32 速度','16bit整数、単位は1.0または0.1mm/s。0では移動しない。','Speed_mm_sはLREAL、送信時は実機の単位で割ってUINT化。','同じ20mm/sでもRaw20か200かが設定で変わるため。','単位は仕様。内部LREALと補助変数は設計。'],
 [8,'MJ0384 6-32 加減速度','16bit整数、0.01G、加速・減速は共通。初期値の自動適用なし。','AccDec_GはLREAL、G×100で送信整数へ換算。','AccとDecを別々に作っても通信には別項目がない。','共通項目・単位は仕様。名前は設計。'],
 [9,'MJ0384 6-32 押付け制限','255が100%、510が200%。50%の記載例は127。','PushLimit_pctはLREAL、%×255÷100を整数化する。','%の値をそのまま送ると、指定した押付け力と一致しない。','詳細単位は仕様。適用上限は機種別確認。'],
 [10,'MJ0384 6-33 制御信号','1ワード内にDSTR・SON・HOME等、bitごとの意味がある。','Controlを15個のBOOLで作り、通信前に制御WORDへ組み立てる。','各指令を名前で扱える。予約b9にはメンバーを作らない。','bit位置は仕様。BOOL構造体のまとめ方は設計。'],
 [11,'MJ0384 6-34 現在位置','32bit符号付き、0.01mm。負数は2の補数。','受信2UINTを結合しDINTとして解釈、×0.01してActualPos_mmへ。','2ワードを別々の現在位置として表示しない。','符号・単位は仕様。内部LREALは設計。'],
 [12,'MJ0384 6-31／6-34 電流','32bit整数mA。RCON-PCのパルスモーターは指令電流。','Current_mAはDINT。2ワードから符号を維持して復元する。','実測トルクや実測押付け力と取り違えない。','意味は仕様。変数名は今回の設計。'],
 [13,'MJ0384 6-34 現在速度','16bit整数、マイナス方向は2の補数。','RawはUINTだがINTとして再解釈し、実機単位を掛けLREALへ。','655xxのような値を巨大な正速度と誤解しない。','符号の意味は仕様。表示型は設計。'],
 [14,'MJ0384 6-34／6-35 状態','PEND・HEND・SV・ALM等がbitに割付。予約b6・b9～11。','Statusを12個のBOOLへ分解する。AlarmCodeはUINTで別に持つ。','異常の有無と異常番号、要求と応答を別々に扱う。','bit位置は仕様。構造体名は設計。'],
 [15,'MJ0384 6-1と固定領域','軸の前にゲートウェイ・リンク・電源等の共通情報がある。','共通Rawは軸構造体へ無理に含めない。DataValidは別途算出。','軸状態だけで通信正常やデータ有効を断定しない。','共通領域は仕様。DataValidの判定設計は未実装。'],
 [16,'同じ8ワード構成が6軸続く','各軸で同じデータ項目を使う。','1軸分の型を作りARRAY[1..6]で6個使う。','同じ定義を6回作らず、修正箇所を共通化できる。','配列・軸呼称は今回の設計。'],
 [17,'Sysmac SBCA-470 4-68～4-70','構造体型を登録し、その下へメンバーを追加して型を指定する。','子型Control／Statusを先に、親型OUT_Axis／IN_Axisを後に登録。','親のメンバー型として子型を選べる状態にしておく。','画面操作は取説。登録順は依存関係による設計。'],
 [18,'MJ0384 6-125 運転手順','データ設定後DSTR立上りで受付。PEND OFF確認と10ms以上保持。','起動・受付・完了・異常・タイムアウトをシーケンスで管理。','型と変数を登録しただけでは安全に動作するプログラムにならない。','タイミングは仕様。安全許可・タイムアウト値は要設計。']
],{height:100});
table(process,28,['資料ID','資料名','参照箇所','確認内容','所在・案内','注意'],[
 ['S1','IAI RCONシステム MJ0384-9D','6-1／6-3／6-30～6-35／6-125','通信構成・単位・bit・運転の受付手順','同じ設備資料の「取説」フォルダ','ページは紙面の章番号。PDFビューアの通し番号ではない。'],
 ['S2','IAI Gateway ESI V1.08 Rev0','RCGW-ECT(112Byte/112Byte)','2003／2004、各56ポート、16bit UINT','取説フォルダの公式XML','Motion/ECMや単体PCON用の別ESIと混同しない。'],
 ['S3','Sysmac Studio操作 SBCA-470AM','4-68～4-70／4-16～4-20','構造体登録／I/Oマップのコピー・貼付','このPCのSysmac Studio付属マニュアル','参照した版。最新であるとの主張ではない。'],
 ['S4','オムロン公式 操作動画','STプログラミング：変数の登録／追加','変数名とデータ型を別々に登録する画面操作','https://www.fa.omron.co.jp/product/tool/ss-video-manual/ja/st-programming/variable-registration/','構造体の名前は本資料独自。公式のRCON専用型ではない。']
],{height:77});
table(process,35,['確認順','次に別機器を扱うとき','記録する内容','判断の例','避ける誤り','確認先'],[
 [1,'通信方式・型式・モードを特定','EtherCAT／EtherNet/IP、機器末尾、モード','同じ機器でもモードが違えばI/O内容が違う','外観や旧プロジェクトだけで決めない','実機銘板・設定の読取り'],
 [2,'入出力方向を決める','PLC基準のOUTとIN','機器のReceiveはPLCのOUTの場合がある','機器側の入出力表記をそのまま流用しない','取説の方向説明'],
 [3,'データ幅・符号・単位を拾う','16/32bit、符号、0.01mm、予約bit','32bit符号付きならDINTで解釈','ESIのUINTだけで意味を決めない','詳細信号一覧・注記'],
 [4,'通信型と内部型を分ける','Raw型／復元型／人が使う型','UINT2個／DINT／LREAL mm','LREAL構造体をそのまま通信へ置かない','ESIとCPU型仕様'],
 [5,'変換の往復を机上確認','正数・負数・上位非0・境界値','入力と復元したmmが一致するか','0だけの試験で完了しない','単位・分割・符号の試験'],
 [6,'動作の受付と応答を読む','開始エッジ、保持、完了、異常','指令が出たことと受け付けたことを区別','StartだけONすれば完成と考えない','タイミング図・運転手順'],
 [7,'安全停止と通常停止を区別','安全回路、範囲、ブレーキ、退避位置','STPは通常の一時停止機能','通信BOOLを安全機能の代用にしない','機械リスク評価・メーカー仕様']
],{height:82});

// 学習計算：編集できる黄色セルと、計算するセルを分離する。実機の設定値ではない。
const learn=base('解説_単位と上下ワード',[32,18,15,49,20,73],56);learn.tabColor='#6C668C';
title(learn,'単位換算・分割・結合をExcelで学ぶ','F','黄色セルは学習用に変更可能。実機に出力しません。数値例は移動範囲・運転条件の推奨ではありません。');
table(learn,5,['段階・項目','学習用入力','単位','計算内容','計算結果','意味'],[
 ['1 目標位置',25.4,'mm','mm×100を四捨五入',null,'人が使う値。通信の最小単位0.01mmへ換算する。'],
 ['2 32bitのビット表現',null,'整数','符号付き値を0～2^32-1へ置換',null,'負数の場合も同じ32bitパターンを保持する。'],
 ['3 OUT 下位ワード',null,'UINT','32bitビット表現を65536で割った余り',null,'TargetPosLoRawに渡す16bit。'],
 ['4 OUT 上位ワード',null,'UINT','32bitビット表現を65536で割った整数部',null,'TargetPosHiRawに渡す16bit。上位を常に0にしない。'],
 ['5 IN 結合の練習',null,'32bit','下位＋上位×65536',null,'分割と逆の処理。ここではOUT値を使って往復を練習する。'],
 ['6 符号付きに復元',null,'DINT','2^31以上なら2^32を引く',null,'DWORDのビット表現からDINTの数値を読み取る考え方。'],
 ['7 mmへ戻す',null,'mm','符号付き整数÷100',null,'最初の入力と一致すれば単位と符号の往復が確認できる。']
],{height:50});
const f={E6:'=ROUND(B6*100,0)',E7:'=MOD(E6,4294967296)',E8:'=MOD(E7,65536)',E9:'=INT(E7/65536)',E10:'=E8+E9*65536',E11:'=IF(E10>=2147483648,E10-4294967296,E10)',E12:'=E11/100'};
for(const [a,v] of Object.entries(f))learn.getRange(a).formulas=[[v]];
learn.getRange('B6').format.fill=palette.amber;learn.getRange('B6').setNumberFormat('0.00');learn.getRange('E6:E11').setNumberFormat('0');learn.getRange('E12').setNumberFormat('0.00');
table(learn,14,['項目','学習用入力','単位','計算内容','計算結果','意味'],[
 ['位置決め幅',0.1,'mm','mm×100を四捨五入',null,'初期値の自動引用はない。別途指定する。非負を前提。'],
 ['速度',20,'mm/s','速度÷1カウント量',null,'単位を間違えると10倍違う指令になる。'],
 ['速度の1カウント量',0.1,'mm/s','例として0.1を設定',null,'学習用。実機が1.0か0.1かは別途読取り確認する。'],
 ['加減速度',0.2,'G','G×100を四捨五入',null,'加速と減速で共通の1項目。'],
 ['押付け電流制限',50,'%','%×255÷100の整数部',null,'取説の50%→127例に合わせた学習式。上限は機種別。']
],{height:53});
learn.getRange('E15').formulas=[['=IF(B15<0,"非負で指定",ROUND(B15*100,0))']];
learn.getRange('E16').formulas=[['=IF(OR(B17=1,B17=0.1),ROUND(B16/B17,0),"単位未確認")']];
learn.getRange('E17').formulas=[['=B17']];learn.getRange('E18').formulas=[['=ROUND(B18*100,0)']];learn.getRange('E19').formulas=[['=INT(B19*255/100)']];learn.getRange('B15:B19').format.fill=palette.amber;learn.getRange('B15:B19').setNumberFormat('0.00');
learn.getRange('B17').dataValidation={rule:{type:'list',values:['1','0.1']}};
table(learn,22,['算術試験（運転値ではない）','入力mm','32bit整数','下位／上位の読み方','下位UINT','上位UINT'],[
 ['取説の正数例',25.4,null,'下位だけに収まる',null,null],
 ['上位が非0になる例',700.25,null,'65535カウントを超えると上位にも値が入る',null,null],
 ['負数の例',-25.4,null,'負数は2の補数。上位65535は異常ではない',null,null],
 ['ゼロの例',0,null,'下位0／上位0',null,null]
],{height:50});
for(let r=23;r<=26;r++){learn.getRange(`C${r}`).formulas=[[`=ROUND(B${r}*100,0)`]];learn.getRange(`E${r}`).formulas=[[`=MOD(MOD(C${r},4294967296),65536)`]];learn.getRange(`F${r}`).formulas=[[`=INT(MOD(C${r},4294967296)/65536)`]];}
learn.getRange('B23:B26').setNumberFormat('0.00');
table(learn,29,['bitの学習','ON/OFF例','論理bit','説明','計算するWORD','注意'],[
 ['サーボON要求',true,4,'SONは論理b4',null,'計算値16は論理ワード。実通信のバイト順は別に確認。'],
 ['開始要求',false,0,'DSTRは論理b0',null,'Startを常時ONにする例ではない。'],
 ['制御ワードの組合せ',null,'b4＋b0','TRUEの指令のマスクを足す',null,'他の指令はOFFという学習例。予約b9は0。']
],{height:55});
learn.getRange('E30').formulas=[['=IF(B30,2^C30,0)']];learn.getRange('E31').formulas=[['=IF(B31,2^C31,0)']];learn.getRange('E32').formulas=[['=SUM(E30:E31)']];learn.getRange('B30:B31').format.fill=palette.amber;
table(learn,35,['順番','処理の段階','型','考え方','配置する場所','実装時の注意'],[
 [1,'OUTの位置を整数化','LREAL→DINT','25.40mmを2540カウントにする','PLCの変換処理','端数の丸め規則・機械範囲・整数範囲を先に決める。'],
 [2,'OUTの位置を分割','DINT→DWORD→2UINT','ビット表現を保って下位16bitと上位16bitを抽出','PLCの変換処理','負数を符号なしへ単純な数値変換しない。'],
 [3,'INの位置を結合','2UINT→DWORD→DINT','上位を16bitずらし下位とOR、そのビットを符号付き解釈','PLCの変換処理','ワード順・バイト順が実機と一致するか確認。'],
 [4,'INの位置をmm化','DINT→LREAL','復元した整数へ0.01を掛ける','PLCの変換処理','型変換命令の丸め・符号の動作はCPU命令仕様で確認。'],
 [5,'Controlを送信','BOOL群→WORD→UINT','取説の各bit位置へON/OFFを詰める','出力は一か所で管理','構造体メモリーのBOOL順をそのまま利用しない。'],
 [6,'Statusを受信','UINT→WORD→BOOL群','取説のマスクで各bitを取り出す','入力デコード処理','PENDとMENDを混同せず、異常と空振りも確認。']
],{height:73});
table(learn,44,['疑問','答え','理由','確認する値','確認する場面','対策'],[
 ['25.40をUINTへ入れてよい？','そのままでは不可','通信は0.01mmの整数なので2540へ換算','単位と型','送信前','人の単位と通信の単位を区別する。'],
 ['上位は0で固定してよい？','不可','大きな正数・負数では上位にもデータがある','正数・負数・上位非0','机上試験','2ワード全体で32bitを表す。'],
 ['構造体を登録したら動く？','動かない','Raw変換と指令受付シーケンスが未実装','変換・起動・応答','登録後','次の解説タブで工程を確認する。'],
 ['Excelの計算をコピーすればPLCで動く？','動かない','学習式とPLCの命令・型変換は異なる','CPU・Sysmac版','実装前','CPU対応命令で作り、ビルドとオフライン試験を行う。']
],{height:65});

const ops=base('解説_登録と動作確認',[12,33,70,69,24],54);ops.tabColor='#6C668C';
title(ops,'登録・変換・動作確認の進め方','E','資料の登録作業と、機械を動かす作業は別工程。既存稼働設備は停止・バックアップ・権限確認を先に行う。');
table(ops,6,['順番','作業','具体的な操作・判断','確認すること','段階'],[
 [1,'既存データの保全','PLCプロジェクトとRCON設定のバックアップを保存。既存I/Oとラダー参照を調べる。','稼働中の設定を無断で書き換えない。','事前確認'],
 [2,'実機設定の読取り','各軸の動作モード・軸順・占有情報・速度単位・有効軸を確認する。','全6軸直接数値指定・追加占有なしという前提に合うか。','事前確認'],
 [3,'通信サイズの設計','各方向112Byte、RCGW-ECTの対応ESIを選ぶ計画を作る。','RCONとSysmacのサイズ・ProductCode・Revisionが一致するか。','設定変更は別作業'],
 [4,'構造体エディタを開く','プログラミング→データ→データ型→構造体型。','SBCA-470 4-68～4-70に記載の画面。','オフライン登録'],
 [5,'子の型を作る','登録ガイドの順1 OUT_Control、順2 IN_Statusを新規作成。','OUT15BOOL、IN12BOOL。予約bitを独自に増やさない。','オフライン登録'],
 [6,'メンバーを入力','型を選び右クリック→メンバ新規作成。各表A列名・B列型・C列コメントを登録。','型全体のTYPE/STRUCT参考文をSTプログラム欄へ貼らない。','オフライン登録'],
 [7,'親の型を作る','順3 OUT_Axis、順4 IN_Axisを作成し、数値とControl／Statusの型を指定。','子構造体型はBOOLやWORDではなく指定のST_型を選ぶ。','オフライン登録'],
 [8,'グローバル変数を作る','RCON1_OUT／RCON1_INを各ARRAY[1..6] OF対応Axis型として登録。','1軸目[1]がRCON軸No.0。起動指令を保持しない。','オフライン登録'],
 [9,'補助変数を登録','RCON1_SpeedUnit_mm_sをLREALで登録。実機読取りで単位を確定する。','1.0または0.1。学習シートの0.1を実機値と思い込まない。','オフライン登録'],
 [10,'Raw変数をI/Oマップへ','OUT_IO／IN_IO各A2:B57をコピー。112Byte版の各方向00ポートの変数欄へ。','コピー列・順序・対象ノードを照合。既存変数へ無条件に貼らない。','オフライン登録'],
 [11,'共通領域を設計','ゲートウェイ制御MON、軸リンク、電源状態等の共通Raw処理を確認。','軸配列だけでは通信制御全体は完成しない。','プログラム設計'],
 [12,'変換処理を作る','OUTの整数化・分割・bit組立、INの結合・符号・単位・bit分解を実装。','本資料は設計一覧。実行する変換プログラムは含まない。','プログラム設計'],
 [13,'データ有効性を判定','通信・軸リンク・割付等の条件からDataValidを算出する。','DataValidは受信bitではなく内部判定。初期FALSE。','プログラム設計'],
 [14,'ビルド・机上検証','型の参照・変数名・配列境界・予約bit・上下ワード・符号を確認。','正数・負数・上位非0・単位1.0/0.1・範囲外を試験。','実機前の確認'],
 [15,'1軸の読取り確認','機械の安全を確保した上で、現在位置とIAI側表示を照合する計画で進める。','0だけでなく既知の位置で符号・桁・速度単位を照合。','実機試験は別途'],
 [16,'1軸の小移動確認','範囲・安全・通信・座標・サーボ等の許可条件を満たして試験する。','縦軸・ブレーキ・治具干渉に注意。BrakeReleaseを安易にONしない。','実機試験は別途'],
 [17,'6軸へ展開','1軸で確認した変換を同じ型の各軸へ適用し、個別に照合。','軸番号と機構の対応は実機で確認。全軸同時に試さない。','実機試験は別途']
],{height:86});
table(ops,27,['段階','運転シーケンスの考え方','OUT側','IN側・確認','注意'],[
 [1,'運転許可を確認','StartはOFF','通信・リンク・異常・原点/座標・サーボ等','別途安全回路と機械範囲確認。'],
 [2,'移動データを確定','目標位置・幅・速度・共通加減速を設定して変換','停止状態等を確認','加減速・位置決め幅の初期値は自動引用されない。'],
 [3,'開始を指令','Control.StartをONしDSTRを送る','PENDのOFF応答を待つ','DSTR立上りでデータ受付。'],
 [4,'受付を確認して指令OFF','ONから10ms以上、かつPEND OFF確認後にStart OFF','受付待ちタイムアウト・異常を監視','DSTR OFFまで指令データを保持する。'],
 [5,'動作完了を確認','次の指令は勝手に上書きしない','今回の受付後のPEND再ON、位置、異常等を確認','MENDは空振りも含む。単独で成功としない。'],
 [6,'箱詰めの次工程へ','機構に合う順番で次の移動条件を設定','軸別完了と干渉条件を確認','モードが衝突回避・軸間補間を自動で行うわけではない。']
],{height:85});
table(ops,37,['項目','確認状況','この資料で確認したこと','これから必要なこと','対象'],[
 ['型・名前・参照','資料内で検証','4構造体39メンバー、6軸配列、全参照先','実際のSysmacで登録とビルド','オフライン'],
 ['通信I/O','ESIと照合','各方向56ポート・全UINT・軸境界','実機モード・軸順・追加占有・バイト順','実機設定'],
 ['単位・計算','学習式を検証','上下ワード・負数・速度単位切替の計算','対象軸の範囲・速度単位・丸め規則','変換処理'],
 ['起動・安全','手順の説明のみ','取説の開始・受付・完了手順を整理','許可・タイムアウト・異常処理・実機安全確認','実装未実施']
],{height:70});

// データ型依存・参照先の検証。内部構造体は通信の固定レイアウトではない。
const known=new Set(['BOOL','UINT','DINT','LREAL']);
for(const d of defs){for(const m of d.members)if(!known.has(m.type))throw Error('未定義型 '+m.type);known.add(d.name);}
function resolve(path){const match=path.match(/^RCON1_(OUT|IN)\[([1-6])\]\.(.+)$/);if(!match)throw Error('参照名不正 '+path);let type=`ST_RCON_Direct_${match[1]}_Axis`;for(const p of match[3].split('.')){const m=defs.find(d=>d.name===type)?.members.find(x=>x.name===p);if(!m)throw Error('メンバー参照不正 '+path);type=m.type;}return type;}
for(const dir of ['OUT','IN'])for(const r of io[dir])if(/^RCON1_/.test(r[6]))resolve(r[6]);
if(defs.length!==4||defs.reduce((a,d)=>a+d.members.length,0)!==39)throw Error('構造体数不正');
if(new Set([...io.OUT,...io.IN].map(r=>r[0])).size!==112)throw Error('I/O名重複');
wb.recalculate();
if(guide.getRange('B28').values[0][0]!==56||guide.getRange('B29').values[0][0]!==112)throw Error('容量式不正');
for(const [mm,lo,hi] of [[25.4,2540,0],[700.25,4489,1],[-25.4,62996,65535],[0,0,0]]){
 learn.getRange('B6').values=[[mm]];wb.recalculate();
 if(learn.getRange('E8').values[0][0]!==lo||learn.getRange('E9').values[0][0]!==hi||Math.abs(learn.getRange('E12').values[0][0]-mm)>1e-9)throw Error('往復計算不正 '+mm);
}
learn.getRange('B6').values=[[25.4]];
for(const [unit,result] of [[1,20],[0.1,200],[0,'単位未確認']]){learn.getRange('B17').values=[[unit]];wb.recalculate();if(learn.getRange('E16').values[0][0]!==result)throw Error('速度式不正');}
learn.getRange('B17').values=[[0.1]];learn.getRange('B31').values=[[true]];wb.recalculate();if(learn.getRange('E32').values[0][0]!==17)throw Error('bit組合せ不正');learn.getRange('B31').values=[[false]];wb.recalculate();
const err=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:1500});
console.log('ERROR_SCAN '+err.ndjson);
console.log((await wb.inspect({kind:'table',range:'登録ガイド!A24:D30',include:'values,formulas',tableMaxRows:8,tableMaxCols:4,maxChars:1800})).ndjson);
await fs.mkdir(previews,{recursive:true});
// 全タブを確認し、長い解説は前半・後半を別々に描画する。
const views=[
 ['登録ガイド','A2:D21','01-guide-top'],['登録ガイド','A24:D48','02-guide-bottom'],
 ['OUT型・メンバー','A6:F24','03-out-control'],['OUT型・メンバー','A27:F35','04-out-axis'],
 ['IN型・メンバー','A6:F21','05-in-status'],['IN型・メンバー','A24:F32','06-in-axis'],
 ['組合せ例・型選び','A2:D15','07-combinations'],['組合せ例・型選び','A18:D35','08-type-choice'],['組合せ例・型選び','A38:D44','09-renaming'],
 ['OUT_IO','A1:F17','10-out-io'],['OUT_IO','A50:I57','11-out-last'],['IN_IO','A1:F17','12-in-io'],['IN_IO','A50:I57','13-in-last'],
 ['解説_取説から設計','A2:F15','14-process-first'],['解説_取説から設計','A16:F24','15-process-second'],['解説_取説から設計','A28:F42','16-process-sources'],
 ['解説_単位と上下ワード','A2:F19','17-learning'],['解説_単位と上下ワード','A22:F32','18-learning-cases'],['解説_単位と上下ワード','A35:F48','19-learning-notes'],
 ['解説_登録と動作確認','A2:E16','20-registration'],['解説_登録と動作確認','A17:E23','21-implementation'],['解説_登録と動作確認','A27:E41','22-sequence']
];
for(const [sheetName,range,name] of views){const b=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(new URL(name+'.png',previews),new Uint8Array(await b.arrayBuffer()));console.log('RENDER '+name);}
try{await fs.access(output);throw Error('同名ファイルがあるため上書き中止');}catch(e){if(e.code!=='ENOENT')throw e;}
await (await SpreadsheetFile.exportXlsx(wb)).save(output);
await fs.writeFile(new URL('./manifest.json',import.meta.url),JSON.stringify({output,defs,io,blockRows,views},null,2));
console.log(JSON.stringify({output,sheets:9,types:4,members:39,rawPorts:112,previewCount:views.length}));
