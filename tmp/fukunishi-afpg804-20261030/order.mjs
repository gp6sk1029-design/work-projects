import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {FileBlob, SpreadsheetFile, Workbook} from '@oai/artifact-tool';

// 原紙を基に入力を準備し、実ブックへの反映は照合後に行う。
const base=new URL('.',import.meta.url);
const info=JSON.parse(await fs.readFile(new URL('inspection.json',base),'utf8'));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(info.source));
const sh=wb.worksheets.getItem('原紙');
if(process.argv[2]==='match'){
  const actual=wb.worksheets.getItem('10.30');
  const audit=Workbook.create();
  const a=audit.worksheets.add('照合');
  a.getRange('A1:D1').values=[['項目','見積書・指示','注文書','判定']];
  const expected=[['型式','AFPG804','B17'],['数量',10,'E17'],['単価',1050,'F17'],['明細金額',10500,'G17'],['税別合計',10500,'G41'],['注文番号','AF-K261030-1','C9'],['請求先','生産技術部','C10'],['納入先','生産技術部 幸田宛','C11']];
  a.getRange('A2:D9').values=expected.map(([label,value,addr])=>{const got=actual.getRange(addr).values[0][0];if(got!==value)throw new Error(`照合不一致 ${addr}: ${got}`);return [label,value,got,'一致'];});
  a.getRange('A1:D9').format.columnWidth=24;
  a.getRange('A1:D9').format.rowHeight=25;
  a.getRange('A1:D1').format={fill:'#16324F',font:{bold:true,color:'#FFFFFF'}};
  a.getRange('B4:C6').setNumberFormat('#,##0');
  a.getRange('B9:C9').format.columnWidth=32;
  a.getRange('A11:D11').merge();
  a.getRange('A11').values=[['見積No. QT080-20261030-3／画像と保存後の注文書を照合']];
  audit.recalculate();
  console.log((await audit.inspect({kind:'table',range:'照合!A1:D9',include:'values',tableMaxRows:9,tableMaxCols:4,maxChars:2200})).ndjson);
  const p=await audit.render({sheetName:'照合',range:'A1:D11',scale:1.5,format:'png'});
  await fs.writeFile(new URL('match.png',base),new Uint8Array(await p.arrayBuffer()));
  await(await SpreadsheetFile.exportXlsx(audit)).save(fileURLToPath(new URL('照合表.xlsx',base)));
}else if(process.argv[2]==='inspect'){
  const p=await wb.render({sheetName:'原紙',range:'B2:H44',scale:1.5,format:'png'});
  await fs.writeFile(new URL('before.png',base),new Uint8Array(await p.arrayBuffer()));
  console.log((await wb.inspect({kind:'table',range:'原紙!B8:H11',include:'values,formulas',tableMaxRows:4,tableMaxCols:7,maxChars:1600})).ndjson);
}else{
  const edits=JSON.parse(await fs.readFile(new URL('edits.json',base),'utf8'));
  for(const [cell,value]of Object.entries(edits))sh.getRange(cell).values=[[value]];
  wb.recalculate();
  const row=sh.getRange('G17').values[0][0];
  const total=sh.getRange('G41').values[0][0];
  if(row!==10500||total!==10500)throw new Error(`金額不一致: ${row}/${total}`);
  const scan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1800});
  console.log(scan.ndjson);
  const p=await wb.render({sheetName:'原紙',range:'B2:H44',scale:1.5,format:'png'});
  await fs.writeFile(new URL('after.png',base),new Uint8Array(await p.arrayBuffer()));
  console.log((await wb.inspect({kind:'table',range:'原紙!B17:H17',include:'values,formulas',tableMaxRows:1,tableMaxCols:7,maxChars:1800})).ndjson);
  await(await SpreadsheetFile.exportXlsx(wb)).save(fileURLToPath(new URL('authored.xlsx',base)));
}
