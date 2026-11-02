import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

// 出力する資料だけを新規作成し、実機・既存プロジェクトは変更しない。
const outputDir='C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/資料/RCON_直接数値指定_6軸_IO構造体_20261017A';
const previewDir=new URL('./previews/',import.meta.url);
const out=[],input=[];
const controls=[
 [0,'DSTR','Start','位置決め開始。受付応答確認・10ms以上保持が必要'],
 [1,'HOME','Home','原点復帰指令'],
 [2,'STP','Pause','一時停止。TRUEで停止、FALSEで解除（安全停止とは別）'],
 [3,'RES','Reset','アラームリセット指令'],
 [4,'SON','ServoOn','サーボON指令'],
 [5,'JISL','InchingSelect','TRUE：インチング、FALSE：ジョグ'],
 [6,'JVEL','JogSpeedSelect','ジョグ速度・インチング距離の切替'],
 [7,'JOG-','JogMinus','原点方向ジョグ'],
 [8,'JOG+','JogPlus','反原点方向ジョグ'],
 [10,'GSL0','GainSelect0','サーボゲインセット選択の下位bit'],
 [11,'GSL1','GainSelect1','サーボゲインセット選択の上位bit'],
 [12,'PUSH','PushEnable','TRUE：押付け、FALSE：通常位置決め'],
 [13,'DIR','PushDirection','押付け方向指定（CON方式選択時）'],
 [14,'INC','RelativeMove','TRUE：相対位置、FALSE：絶対位置'],
 [15,'BKRL','BrakeRelease','ブレーキ強制解除。通常FALSE・使用時は機械安全確認']
];
const statuses=[
 [0,'PEND','PositionDone','位置決め完了'],[1,'HEND','HomeDone','原点復帰完了'],
 [2,'MOVE','Moving','移動中'],[3,'ALM','Alarm','アラーム発生'],
 [4,'SV','ServoReady','サーボON・運転準備完了'],[5,'PSFL','PushMiss','押付け空振り'],
 [7,'ALML','OverloadWarning','過負荷警告・軽故障アラーム'],
 [8,'MEND','CommandDone','指令完了（位置決め・押付け・空振りを含む）'],
 [12,'ZONE1','Zone1','ゾーン1内'],[13,'ZONE2','Zone2','ゾーン2内'],
 [14,'CRDY','ControllerReady','コントローラー準備完了'],
 [15,'EMGS','EmergencyStop','非常停止状態のモニター（安全回路の代用不可）']
];
const definitions=[
 {name:'ST_RCON_DirectControl',comment:'直接数値指定の制御BOOL群',members:controls.map(([bit,sig,member,comment])=>[member,'BOOL',comment,'ON/OFF',`制御ワードb${bit} ${sig}`])},
 {name:'ST_RCON_DirectStatusBits',comment:'直接数値指定の状態BOOL群',members:statuses.map(([bit,sig,member,comment])=>[member,'BOOL',comment,'ON/OFF',`状態ワードb${bit} ${sig}`])},
 {name:'ST_RCON_DirectCommand',comment:'人が指定する移動指令（工学単位）',members:[
  ['TargetPos_mm','LREAL','目標位置。絶対／相対はControl.RelativeMoveで区別','mm','DINTへ0.01mm換算後、目標位置L/Hへ分割'],
  ['PositionBand_mm','LREAL','位置決め幅。非負・仕様範囲内で指定','mm','非負整数へ0.01mm換算（UDINTは内部の推奨型）'],
  ['Speed_mm_s','LREAL','指令速度。実機速度単位・上限に合わせて換算','mm/s','UINTへ換算。1.0または0.1mm/s単位'],
  ['AccDec_G','LREAL','加速・減速共通値。個別指定ではない','G','UINTへ0.01G換算'],
  ['PushLimit_pct','LREAL','押付け電流制限。適用範囲はアクチュエーター仕様を確認','%','UINTへ換算。255=100%、50%の例は127'],
  ['Control','ST_RCON_DirectControl','制御BOOL群をWORDにまとめてからUINTへ渡す','構造体','予約b9は使用禁止。出力は一か所で管理']
 ]},
 {name:'ST_RCON_DirectFeedback',comment:'受信データを復元した取得値',members:[
  ['ActualPos_mm','LREAL','現在位置。符号付き32bitを復元して換算','mm','DINTの現在位置L/Hを復元後に0.01倍'],
  ['Current_mA','DINT','RCON-PCでは指令電流。実測トルクではない','mA','現在電流L/Hを符号付き32bitとして復元'],
  ['ActualSpeed_mm_s','LREAL','現在速度。移動方向の符号を保持','mm/s','16bitをINTとして解釈し実機速度単位を乗算'],
  ['AlarmCode','UINT','アラームコード。簡易アラームコードではない','コード','アラームコードワードを取得'],
  ['Status','ST_RCON_DirectStatusBits','状態WORDから各BOOLを取り出す','構造体','予約b6,b9～11は使用しない'],
  ['DataValid','BOOL','通信・軸リンク・割付確認を含む有効性。初期FALSE','ON/OFF','PLC側で別途判定する内部値。単一PDOには対応しない']
 ]},
 {name:'ST_RCON_DirectAxis',comment:'1軸分の指令とフィードバック',members:[
  ['Cmd','ST_RCON_DirectCommand','PLCから指定する移動データ・制御','構造体','通信へのエンコード処理を別途実装'],
  ['Fbk','ST_RCON_DirectFeedback','RCONから受信した取得値・状態','構造体','通信からのデコード処理を別途実装']
 ]}
];
const knownTypes=new Set(['BOOL','UINT','DINT','LREAL']);
for(const def of definitions){
 if(new Set(def.members.map(m=>m[0])).size!==def.members.length)throw Error('メンバ名重複');
 for(const m of def.members){if(!knownTypes.has(m[1]))throw Error('未定義の型参照 '+m[1]);}
 knownTypes.add(def.name);
}
const commonOut=[
 ['GwControl0Raw','ゲートウェイ制御信号0（MON等）','WORD','共通制御','16bit一括'],
 ['GwControl1ReservedRaw','ゲートウェイ制御信号1（予約・使用禁止）','-','-','予約'],
 ...Array.from({length:6},(_,i)=>['ReservedOut'+String(i+2).padStart(2,'0')+'Raw','共通予約領域（使用禁止・占有あり）','-','-','予約'])
];
const commonIn=[
 ['GwStatus0Raw','ゲートウェイ状態信号0','WORD','共通状態','16bit一括'],
 ['AxisLinkStatusRaw','ゲートウェイ状態信号1（軸No.0～15リンク状態）','WORD','軸リンク状態','16bit一括'],
 ...Array.from({length:4},(_,i)=>['PowerStatus'+i+'Raw','電源ユニット状態信号'+i,'WORD','電源状態','16bit一括']),
 ['PowerStatus4MaintenanceRaw','電源ユニット状態信号4／軽故障メンテナンス（設定依存）','WORD','共通状態','16bit一括'],
 ['ReservedIn07Raw','共通予約領域（使用禁止・占有あり）','-','-','予約']
];
function add(rows,prefix,n,axis,field,comment,decoded,member,unit){
 const port=prefix+String(n).padStart(2,'0');
 const name='RCON1_Dir_'+(axis===null?'':`Axis${axis}_`)+field;
 const label=axis===null?'共通':`${axis}軸目（No.${axis-1}）`;
 const obj=(prefix==='OUT'?'2003':'2004')+':'+(n+1).toString(16).toUpperCase().padStart(2,'0');
 const path=axis===null?member:(member==='-'?'-':`RCON1_DirectAxis[${axis}].${member}`);
 rows.push([name,`【${port}】${label} ${comment}`,port,'UINT',decoded,axis===null?'共通':axis-1,path,unit,obj]);
}
for(let n=0;n<8;n++){
 const [f,c,t,m,u]=commonOut[n];add(out,'OUT',n,null,f,c,t,m,u);
 const [g,d,v,p,q]=commonIn[n];add(input,'IN',n,null,g,d,v,p,q);
}
const axisOut=[
 ['TargetPosLoRaw','目標位置 下位ワード','DINT（結合後）','Cmd.TargetPos_mm','0.01mm'],
 ['TargetPosHiRaw','目標位置 上位ワード','DINT（結合後）','Cmd.TargetPos_mm','0.01mm'],
 ['PositionBandLoRaw','位置決め幅 下位ワード','UDINT（内部推奨）','Cmd.PositionBand_mm','0.01mm'],
 ['PositionBandHiRaw','位置決め幅 上位ワード','UDINT（内部推奨）','Cmd.PositionBand_mm','0.01mm'],
 ['SpeedRaw','速度指令','UINT','Cmd.Speed_mm_s','1.0／0.1mm/s（設定依存）'],
 ['AccDecRaw','加減速度指令（加速・減速共通）','UINT','Cmd.AccDec_G','0.01G'],
 ['PushLimitRaw','押付け電流制限値','UINT','Cmd.PushLimit_pct','255＝100％'],
 ['ControlRaw','軸制御信号（DSTR・SON等）','WORD','Cmd.Control','16bit一括']
];
const axisIn=[
 ['ActualPosLoRaw','現在位置 下位ワード','DINT（結合後）','Fbk.ActualPos_mm','0.01mm'],
 ['ActualPosHiRaw','現在位置 上位ワード','DINT（結合後）','Fbk.ActualPos_mm','0.01mm'],
 ['CurrentLoRaw','現在電流 下位ワード（PCは指令電流）','DINT（結合後）','Fbk.Current_mA','mA'],
 ['CurrentHiRaw','現在電流 上位ワード（PCは指令電流）','DINT（結合後）','Fbk.Current_mA','mA'],
 ['ActualSpeedRaw','現在速度（負方向は2の補数）','INT','Fbk.ActualSpeed_mm_s','1.0／0.1mm/s（設定依存）'],
 ['ReservedInRaw','予約領域（使用禁止）','-','-','予約'],
 ['AlarmCodeRaw','アラームコード（簡易コードではない）','UINT','Fbk.AlarmCode','コード'],
 ['StatusRaw','軸状態信号（PEND・SV等）','WORD','Fbk.Status','16bit一括']
];
for(let axis=1;axis<=6;axis++)for(let k=0;k<8;k++){
 const n=8+(axis-1)*8+k;
 add(out,'OUT',n,axis,...axisOut[k]);add(input,'IN',n,axis,...axisIn[k]);
}
// 全56ポート、軸境界、構造体の全参照先を照合。
const ioNames=[...out,...input].map(r=>r[0]);
if(out.length!==56||input.length!==56||new Set(ioNames).size!==112)throw Error('I/O数・名前不一致');
function resolvePath(path){
 const parts=path.replace(/^RCON1_DirectAxis\[[1-6]\]\./,'').split('.');
 let type='ST_RCON_DirectAxis';
 for(const part of parts){const d=definitions.find(d=>d.name===type);const m=d?.members.find(m=>m[0]===part);if(!m)throw Error('構造体参照先不正 '+path);type=m[1];}
}
for(const [prefix,rows] of [['OUT',out],['IN',input]])rows.forEach((r,k)=>{
 if(r[2]!==prefix+String(k).padStart(2,'0')||r[3]!=='UINT'||r[0].length>127)throw Error('ポート順・型不一致');
 if(k>=8&&r[6]!=='-')resolvePath(r[6]);
});
for(let a=1;a<=6;a++){
 const first=8+(a-1)*8;
 if(!out[first][0].endsWith(`Axis${a}_TargetPosLoRaw`)||!out[first+7][0].endsWith(`Axis${a}_ControlRaw`)||!input[first+7][0].endsWith(`Axis${a}_StatusRaw`))throw Error('軸境界不一致');
}
const wb=Workbook.create();
function base(name,headers,rows,widths){
 const s=wb.worksheets.add(name);s.showGridLines=false;
 const last=String.fromCharCode(64+headers.length);
 s.getRange(`A1:${last}${rows.length+1}`).values=[headers,...rows];
 s.getRange(`A1:${last}${rows.length+1}`).format.font={name:'Arial',size:11,color:'#17324D'};
 s.getRange(`A1:${last}${rows.length+1}`).format.rowHeight=36;
 s.getRange(`A1:${last}${rows.length+1}`).format.verticalAlignment='center';
 s.getRange(`A1:${last}1`).format={fill:'#193A5A',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,wrapText:true};
 widths.forEach((w,i)=>s.getRange(`${String.fromCharCode(65+i)}1:${String.fromCharCode(65+i)}${rows.length+1}`).format.columnWidth=w);
 s.freezePanes.freezeRows(1);
 return s;
}
const intro=wb.worksheets.add('概要と登録手順');intro.showGridLines=false;
intro.getRange('A1:D39').format.font={name:'Arial',size:11,color:'#17324D'};
intro.getRange('A1:D39').format.rowHeight=27;
intro.getRange('A1:A39').format.columnWidth=36;intro.getRange('B1:B39').format.columnWidth=18;
intro.getRange('C1:C39').format.columnWidth=22;intro.getRange('D1:D39').format.columnWidth=105;
intro.getRange('A2').values=[['RCON 6軸 直接数値指定 I/O・構造体設計']];intro.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:'#193A5A'};
intro.getRange('A4:D10').values=[
 ['構成','値','単位','前提・確認事項'],['軸数',6,'軸','全軸直接数値指定。軸No.0～5の順番どおり'],
 ['共通固定領域',8,'ワード／方向','電源ユニットなしでも固定領域は占有'],
 ['1軸の占有',8,'ワード／方向','加速・減速は共通の1項目'],
 ['合計',null,'ワード／方向','追加ユニット等の占有がない場合'],
 ['通信サイズ',null,'Byte／方向','RCONとSysmacの双方を同じサイズに合わせる'],
 ['ESIプロファイル','112Byte','入力／出力','RCGW-ECT(112Byte/112Byte)／Rev 0x00010008']
];
intro.getRange('B8').formulas=[['=B6+B5*B7']];intro.getRange('B9').formulas=[['=B8*2']];
intro.getRange('A4:D4').format={fill:'#193A5A',font:{name:'Arial',bold:true,color:'#FFFFFF'}};
intro.getRange('A12:D17').values=[
 ['軸の呼び方','RCON軸No.','I/Oポート番号','内部構造体の要素'],
 ...Array.from({length:6},(_,i)=>[`${i+1}軸目`,i,`${8+i*8}～${15+i*8}`,`RCON1_DirectAxis[${i+1}]`]).slice(0,5)
];
intro.getRange('A18:D18').values=[['6軸目',5,'48～55','RCON1_DirectAxis[6]']];
intro.getRange('A12:D12').format={fill:'#316A9A',font:{name:'Arial',bold:true,color:'#FFFFFF'}};
const instructions=[
 ['資料の用途','I/Oリストと型定義の設計資料。変換・起動ラダーは含まない。'],
 ['1. 設定の事前確認','全6軸の動作モード・占有情報・軸順・速度単位をIAI側設定の読取で確認。'],
 ['2. バックアップ','既存PLC・RCON設定を保存。64Byteポジショナー1用表は直接流用しない。'],
 ['3. 型の登録','構造体定義の登録順1→5で、Sysmacのデータ型エディタに構造体とメンバを登録。'],
 ['4. 変数の登録','変数と単位のグローバル変数を登録。Raw112変数はI/Oマップから登録する。'],
 ['5. 出力の貼付','OUT_IOのA2:B57のみコピーし、対象RCONのOut_OUT00_2003_01の変数セルへ貼付。'],
 ['6. 入力の貼付','IN_IOのA2:B57のみコピーし、In_IN00_2004_01の変数セルへ貼付。'],
 ['貼付時の条件','オフライン・未割付向け。既存変数があれば上書き前にラダーと照合。見出し・C列以降はコピーしない。'],
 ['7. 変換の実装','工学単位とUINTの変換、符号保持、ワード順・バイト順、BOOLの組立／分解を別途実装。'],
 ['構造体の位置付け','内部構造体をPDOへ丸ごと割り付けない。BOOLの並びをメモリー配置と同一とみなさない。'],
 ['8. 運転前確認','安全回路・通信・軸リンク・原点／座標・サーボ・異常・範囲・タイムアウトの確認が必要。'],
 ['制御の注意','DSTRは10ms以上かつPEND OFF応答確認後にOFF。受付中は指令データ保持。'],
 ['現在位置の前提','RCP6等の直動軸用。DDモーターは単位が異なるため、本表のmm換算を流用しない。'],
 ['確認範囲','ESIの112ポート・全6軸境界・型参照を確認。Sysmacビルド・実機貼付・転送・動作試験は未実施。'],
 ['作成日','2026-10-17。物理機構名が未提示のため、1～6軸目で仮命名。'],
 ['出典1','IAI RCONシステム取扱説明書 MJ0384-9D：6-1～6-3、6-30～6-35、6-125。'],
 ['出典2','公式ESI ESI_IAI_Gateway_ECT_V_1_08_Rev_0.xml：112Byte版、2003/2004、各56×UINT。'],
 ['出典3','Sysmac Studio SBCA-470AM：4-68～4-70（構造体登録）、4-16～4-20（I/O貼付）。']
];
instructions.forEach(([a,b],i)=>{intro.getRange(`A${i+21}`).values=[[a]];intro.getRange(`D${i+21}`).values=[[b]];});
intro.tabColor='#193A5A';
const ioHeaders=['変数（コピー）','変数コメント（コピー）','ポート','I/O型','復元・変換時の型','RCON軸No.','内部構造体の対応先','通信単位','Index:SubIndex'];
for(const [sn,rows] of [['OUT_IO',out],['IN_IO',input]]){
 const s=base(sn,ioHeaders,rows,[45,69,14,12,24,16,59,31,19]);
 s.getRange('A2:B57').format.fill='#EAF3FF';s.getRange('B2:B57').format.wrapText=true;
 s.getRange('G2:I57').format.wrapText=true;s.getRange('C2:F57').format.wrapText=true;
 s.tabColor=sn==='OUT_IO'?'#316A9A':'#517F9F';
}
const typeRows=definitions.flatMap((d,i)=>d.members.map(m=>[i+1,d.name,m[0],m[1],m[2],m[3],m[4]]));
const types=base('構造体定義',['登録順','構造体名','メンバ名','データ型','コメント','単位','変換・対応内容'],typeRows,[12,36,27,36,62,16,65]);
types.getRange(`E2:G${typeRows.length+1}`).format.wrapText=true;
let r=2;for(const d of definitions){types.getRange(`A${r}:G${r}`).format.borders={top:{style:'medium',color:'#316A9A'}};r+=d.members.length;}
const bits=[];
for(const [dir,list,type] of [['OUT',controls,'Cmd.Control'],['IN',statuses,'Fbk.Status']]){
 for(let bit=0;bit<16;bit++){
  const entry=list.find(x=>x[0]===bit);
  bits.push([dir,bit,'16#'+(1<<bit).toString(16).toUpperCase().padStart(4,'0'),entry?.[1]??'予約',entry?'BOOL':'使用禁止',entry?`RCON1_DirectAxis[n].${type}.${entry[2]}`:'-',entry?.[3]??'予約ビット。出力は使用禁止、入力は判定に使わない']);
 }
}
const bs=base('ビット割付',['方向','論理bit','論理マスク','信号名','内部型','構造体メンバ（n=1～6）','意味・注意'],bits,[12,13,18,17,14,64,81]);
bs.getRange('F2:G33').format.wrapText=true;
const globals=base('変数と単位',['変数名','データ型','初期値・保持','コメント'],[
 ['RCON1_DirectAxis','ARRAY[1..6] OF ST_RCON_DirectAxis','非保持／BOOLはFALSE','各軸のCmd・Fbk。I/Oマップへ構造体全体を割り付けない。'],
 ['RCON1_DirectSpeedUnit_mm_s','LREAL','未設定（0.0のまま使わない）','実機GW設定の1.0または0.1を確認して設定。0や不明の場合は出力しない。']
],[40,49,36,85]);
globals.getRange('C2:D3').format.wrapText=true;
globals.getRange('A6:F14').values=[
 ['項目','構造体の型','入力・表示単位','通信上の解釈型','換算方法','注意'],
 ['目標位置','LREAL','mm','DINT／32bit','入力mm×100を丸めて32bit化','符号・ソフトストローク・分割時のビット表現を保持'],
 ['位置決め幅','LREAL','mm','非負32bit／UDINT推奨','入力mm×100を丸めて非負整数化','UDINTはPLC内部選定。メーカーの符号なし保証ではない'],
 ['指令速度','LREAL','mm/s','UINT／16bit','入力mm/s÷実機速度単位','実機設定が1.0か0.1かを確認。機械上限と整数範囲も確認'],
 ['加減速度','LREAL','G','UINT／16bit','入力G×100を丸めて整数化','加速・減速共通。初期値の自動引用なし'],
 ['押付け制限','LREAL','%','UINT／16bit','入力%×255÷100を整数化','50%の例は127。許容範囲は対象アクチュエーターに従う'],
 ['現在位置','LREAL','mm','DINT／32bit','受信DINT×0.01','2ワードを結合し符号付きとして解釈する'],
 ['現在速度','LREAL','mm/s','INT／16bit','受信INT×実機速度単位','負方向は2の補数。UINT値をそのまま実速度にしない'],
 ['現在電流','DINT','mA','DINT／32bit','受信2ワードを結合','RCON-PCは指令電流。ACサーボはフィードバック電流']
];
globals.getRange('A6:F6').format={fill:'#193A5A',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:30};
globals.getRange('A7:F14').format.font={name:'Arial',size:11,color:'#17324D'};
globals.getRange('A7:F14').format.rowHeight=48;globals.getRange('A7:F14').format.wrapText=true;
globals.getRange('E1:E14').format.columnWidth=55;globals.getRange('F1:F14').format.columnWidth=73;
globals.getRange('A17:F20').values=[
 ['構造体の使用例（内部値のみ）','','','','',''],
 ['RCON1_DirectAxis[1].Cmd.TargetPos_mm','LREAL','50.00mmの入力例','','','この代入だけでは実機へ出力されない。数値は運転推奨値ではない。'],
 ['RCON1_DirectAxis[1].Cmd.Control.Start','BOOL','起動シーケンスで制御','','','常時TRUEにしない。範囲・安全・通信確認と受付ハンドシェイクが別途必要。'],
 ['RCON1_DirectAxis[6].Fbk.Status.Alarm','BOOL','6軸目の異常判定用','','','Raw状態ワードからのデコードが必要。定義しただけで自動更新されない。']
];
globals.getRange('A17:F20').format.font={name:'Arial',size:11,color:'#17324D'};globals.getRange('A17:F20').format.rowHeight=44;globals.getRange('A17:F20').format.wrapText=true;

wb.recalculate();
if(intro.getRange('B8').values[0][0]!==56||intro.getRange('B9').values[0][0]!==112)throw Error('容量計算不一致');
for(const [sn,rows] of [['OUT_IO',out],['IN_IO',input]])if(JSON.stringify(wb.worksheets.getItem(sn).getRange('A2:I57').values)!==JSON.stringify(rows))throw Error('セル値不一致');
await fs.mkdir(outputDir,{recursive:true});await fs.mkdir(previewDir,{recursive:true});
const xlsxPath=outputDir+'/RCON_直接数値指定_6軸_IOリスト・構造体.xlsx';
try{await fs.access(xlsxPath);throw Error('同名成果物が存在するため上書き中止');}catch(e){if(e.code!=='ENOENT')throw e;}
// 全シートの主要範囲を描画。幅の大きい表はコピー列と対応情報を分けて確認。
const views=[['概要と登録手順','A2:D18','overview'],['概要と登録手順','A21:D38','instructions'],['OUT_IO','A1:F17','out_first'],['OUT_IO','A50:F57','out_last'],['OUT_IO','G10:I17','out_links'],['IN_IO','A1:F17','in_first'],['IN_IO','A50:F57','in_last'],['IN_IO','G10:I17','in_links'],['構造体定義','A1:F22','types_first'],['構造体定義','A23:G42','types_last'],['ビット割付','A1:G17','control_bits'],['ビット割付','A18:G33','status_bits'],['変数と単位','A1:D3','global_vars'],['変数と単位','A6:F14','units'],['変数と単位','A17:F20','usage']];
for(const [sheetName,range,name] of views){const b=await wb.render({sheetName,range,scale:1.15,format:'png'});await fs.writeFile(new URL(name+'.png',previewDir),new Uint8Array(await b.arrayBuffer()));}
const exported=await SpreadsheetFile.exportXlsx(wb);await exported.save(xlsxPath);
// テキスト成果物は呼出し側がapply_patchで作成する。
const supportFiles={
 'OUT_56ワード_貼付用.tsv':out.map(r=>r.slice(0,2).join('\t')).join('\n'),
 'IN_56ワード_貼付用.tsv':input.map(r=>r.slice(0,2).join('\t')).join('\n'),
 '構造体定義_参考.txt':[
  'RCON 6軸 直接数値指定：PLC内部構造体の参考定義',
  'これはSysmacのSTプログラム欄へ貼り付けるものではありません。',
  'Sysmacの「プログラミング→データ→データ型→構造体型」で、Excelの登録順に型とメンバを登録してください。',
  '標準IEC ST表記による設計参照であり、Sysmacへのインポート・ビルド確認は未実施です。',
  '構造体を定義するだけでは通信に接続されません。エンコード／デコード処理は別途必要です。','',
  ...definitions.flatMap(d=>['TYPE '+d.name+' :','STRUCT',...d.members.map(m=>'    '+m[0]+' : '+m[1]+'; (* '+m[2]+' *)'),'END_STRUCT;','END_TYPE','']),
  'グローバル変数の登録例：','RCON1_DirectAxis : ARRAY[1..6] OF ST_RCON_DirectAxis;',
  'RCON1_DirectSpeedUnit_mm_s : LREAL; (* 実機設定の1.0または0.1を確認して設定。未設定値で換算しない *)','',
  '対応例：RCON1_DirectAxis[1].Cmd.TargetPos_mm は1軸目（RCON No.0）の目標位置mmです。',
  'RCON1_DirectAxis[6].Fbk.Status.Alarm は6軸目（RCON No.5）の異常状態です。',
  'Raw変数は別途I/OマップへUINTで登録します。内部構造体のBOOL配置をPDOメモリー配置と同一視しないでください。',
  '制御・状態のbit番号は取説の論理番号です。実通信のワード順・バイト順を照合してから変換処理へ適用してください。'
 ].join('\n')
};
console.log(JSON.stringify({xlsxPath,outputDir,supportFiles,stats:{outWords:56,inWords:56,uniqueRawNames:112,structures:definitions.length,members:typeRows.length,controlBool:controls.length,statusBool:statuses.length,axisCount:6},definitions}));
