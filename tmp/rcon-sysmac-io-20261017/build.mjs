import fs from 'node:fs/promises';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

// 通常EtherCAT、全6軸ポジショナー1、軸No.0～5、追加占有領域なし。
const dest = 'C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/資料/RCON_Sysmac_IO貼付_6軸_20261017A';
const out = [], input = [];
const outCommon = [
 ['RCON1_GwControl0Raw','ゲートウェイ制御信号0（MON等／16bit一括）'],
 ['RCON1_GwControl1ReservedRaw','ゲートウェイ制御信号1（予約・使用禁止）'],
 ...Array.from({length:6},(_,i)=>['RCON1_ReservedOut'+String(i+2).padStart(2,'0')+'Raw','共通予約領域（使用禁止・占有あり）'])
];
const inCommon = [
 ['RCON1_GwStatus0Raw','ゲートウェイ状態信号0（運転・異常等／16bit一括）'],
 ['RCON1_AxisLinkStatusRaw','ゲートウェイ状態信号1（軸No.0～15リンク状態）'],
 ['RCON1_PowerStatus0Raw','電源ユニット状態信号0'],
 ['RCON1_PowerStatus1Raw','電源ユニット状態信号1'],
 ['RCON1_PowerStatus2Raw','電源ユニット状態信号2'],
 ['RCON1_PowerStatus3Raw','電源ユニット状態信号3'],
 ['RCON1_PowerStatus4MaintenanceRaw','電源ユニット状態信号4／軽故障メンテナンス（設定依存）'],
 ['RCON1_ReservedIn07Raw','共通予約領域（使用禁止・占有あり）']
];
for(let k=0;k<8;k++){
 const op='OUT'+String(k).padStart(2,'0'),ip='IN'+String(k).padStart(2,'0');
 out.push([outCommon[k][0],'【'+op+'】'+outCommon[k][1],op,'UINT','共通']);
 input.push([inCommon[k][0],'【'+ip+'】'+inCommon[k][1],ip,'UINT','共通']);
}
for(let axis=1;axis<=6;axis++){
 const pre='RCON1_Axis'+axis+'_',label=axis+'軸目（RCON軸No.'+(axis-1)+'）';
 const o=[['ReservedOut0Raw','予約 第1ワード（使用禁止・占有あり）'],['ReservedOut1Raw','予約 第2ワード（使用禁止・占有あり）'],['CommandPosNoRaw','指令ポジションNo.（0～127）'],['ControlRaw','軸制御信号（サーボON・原点復帰・起動等／16bit一括）']];
 const i=[['ActualPosLoRaw','現在位置 下位ワード（32bitデータの下位16bit）'],['ActualPosHiRaw','現在位置 上位ワード（32bitデータの上位16bit）'],['CompletedPosNoRaw','完了ポジションNo.（異常時は簡易アラームコード）'],['StatusRaw','軸状態信号（位置決め完了・原点復帰完了・異常等／16bit一括）']];
 for(let j=0;j<4;j++){
  const port=8+(axis-1)*4+j,op='OUT'+String(port).padStart(2,'0'),ip='IN'+String(port).padStart(2,'0');
  out.push([pre+o[j][0],'【'+op+'】'+label+' '+o[j][1],op,'UINT',axis-1]);
  input.push([pre+i[j][0],'【'+ip+'】'+label+' '+i[j][1],ip,'UINT',axis-1]);
 }
}
// 行数、ポート順、型、変数名重複、各軸の境界を検証。
if(out.length!==32||input.length!==32)throw Error('行数不一致');
const names=[...out,...input].map(r=>r[0]);
if(new Set(names).size!==64||names.some(n=>!/^[A-Za-z][A-Za-z0-9_]*$/.test(n)||n.length>127))throw Error('変数名不正');
for(const [prefix,rows] of [['OUT',out],['IN',input]]){
 rows.forEach((r,k)=>{if(r[2]!==prefix+String(k).padStart(2,'0')||r[3]!=='UINT'||r.slice(0,2).some(v=>/[\t\r\n]/.test(v)))throw Error('ポート順・型・区切り不正');});
}
for(let a=1;a<=6;a++){
 const p=8+(a-1)*4;
 if(out[p+2][0]!==`RCON1_Axis${a}_CommandPosNoRaw`||out[p+3][0]!==`RCON1_Axis${a}_ControlRaw`||input[p][0]!==`RCON1_Axis${a}_ActualPosLoRaw`||input[p+3][0]!==`RCON1_Axis${a}_StatusRaw`)throw Error('軸境界不一致');
}
const workbook=Workbook.create();
for(const [sn,rows,first] of [['OUT貼付',out,'Out_OUT00_2003_01'],['IN貼付',input,'In_IN00_2004_01']]){
 const s=workbook.worksheets.add(sn);s.showGridLines=false;
 s.getRange('A1:E33').values=[['変数','変数コメント','ポート（コピー不要）','型（コピー不要）','RCON軸No.'],...rows];
 s.getRange('A1:E33').format.font={name:'Arial',size:11,color:'#172B4D'};
 s.getRange('A1:E33').format.rowHeight=34;
 s.getRange('A1:E33').format.verticalAlignment='center';
 s.getRange('A1:E1').format={fill:'#193A5A',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:30};
 s.getRange('A2:B33').format.fill='#EAF3FF';
 s.getRange('A1:A33').format.columnWidth=44;
 s.getRange('B1:B33').format.columnWidth=86;
 s.getRange('B2:B33').format.wrapText=true;
 s.getRange('C1:C33').format.columnWidth=24;
 s.getRange('D1:D33').format.columnWidth=20;
 s.getRange('E1:E33').format.columnWidth=15;
 s.getRange('F1:F33').format.columnWidth=3;
 s.getRange('G1:G23').format.columnWidth=112;
 s.getRange('G1:G23').format.font={name:'Arial',size:11,color:'#172B4D'};
 s.getRange('G1:G23').format.rowHeight=25;
 s.getRange('G1:G23').values=[
  ['貼り付け手順と前提'],
  ['対象：通常EtherCAT／RCGW-ECT(64Byte/64Byte)／全6軸ポジショナー1'],
  ['前提：RCON軸No.0～5が順番どおり・追加占有領域なし。実機の設定は未確認。'],
  ['コピー範囲：A2:B33（32行×2列）。見出し・C～E列はコピーしない。'],
  ['Sysmac：オフラインでI/Oマップの「変数」「変数コメント」を隣接表示。'],
  ['貼付先：対象RCONの '+first+' の「変数」セル。'],
  ['新規・未割付用。既存変数があれば上書きせず、プロジェクトを別名保存して先に照合。'],
  ['全ポートを展開し、番号00～31が欠けずに連続していることを確認。'],
  ['貼付後は先頭00・1軸目08・5軸目24・最終31のポートと名前を確認。'],
  ['貼付エラー・型や変数種別が確定しない場合は転送せず、アウトプット表示を確認。'],
  ['全変数の型はUINT（16bit生データ）。BOOLを直接割り付ける表ではない。'],
  ['Rawは生データ。BOOLへのビット分解・現在位置の32bit復元は別の処理が必要。'],
  ['現在位置は符号付き32bit。下位／上位はワード順であり、バイト順は実機照合が必要。'],
  ['各軸出力の先頭2ワードは予約。ポジショナー1では目標位置を書き込まない。'],
  ['MON・軸制御・予約領域をこの表だけでON/OFFしない。転送・実機試験は未実施。'],
  ['位置・速度・加減速はRCONのポジションテーブルを使用（ポジションNo.0～127）。'],
  ['RCON1は命名用接頭語。ノード番号やゲートウェイ名を変更しない。'],
  ['軸数やモードを変更する場合、割付表を再計算してから使用する。'],
  ['出典：IAI MJ0384-9D 6-1～6-3／6-39（アドレス・ポジショナー1）'],
  ['出典：オムロン SBCZ-914D 29～30（変数登録。簡易直値の位置出力は流用しない）'],
  ['出典：Sysmac操作マニュアル SBCA-470AM 4-16～4-20（表計算から貼付）'],
  ['作成日：2026-10-17／物理軸名称が未提示のため1～6軸目で命名。'],
  ['入力・出力は別々に貼付。予約行も含め32行を保持し、行位置をずらさない。']
 ];
 s.getRange('G1').format.font={name:'Arial',size:14,bold:true,color:'#193A5A'};
 s.freezePanes.freezeRows(1);s.tabColor=sn==='OUT貼付'?'#193A5A':'#316A9A';
}
workbook.recalculate();
await fs.mkdir(dest,{recursive:true});
const path=dest+'/RCON_6軸_ポジショナー1_Sysmac貼付.xlsx';
try{await fs.access(path);throw Error('同名成果物があるため上書き中止');}catch(e){if(e.code!=='ENOENT')throw e;}
for(const sn of ['OUT貼付','IN貼付']){
 const actual=workbook.worksheets.getItem(sn).getRange('A2:E33').values;
 const expected=sn==='OUT貼付'?out:input;
 if(JSON.stringify(actual)!==JSON.stringify(expected))throw Error('セル値と元データが不一致');
 const preview=await workbook.render({sheetName:sn,range:'A1:E14',scale:1.5,format:'png'});
 await fs.writeFile(dest+'/'+(sn==='OUT貼付'?'preview_out':'preview_in')+'.png',new Uint8Array(await preview.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(workbook);await xlsx.save(path);
console.log(JSON.stringify({path,rows:64,uniqueNames:64,outTsv:out.map(r=>r.slice(0,2).join('\t')).join('\n'),inTsv:input.map(r=>r.slice(0,2).join('\t')).join('\n')}));
