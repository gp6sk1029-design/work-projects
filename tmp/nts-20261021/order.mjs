import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';

// 既存ブックは読み込みだけとし、編集結果を作業フォルダへ出力する。
const source = '\\\\nas-ime5\\生産技術部\\1.注文書\\A【経費】 10万円以下 修理部品 消耗部品 等\\A【注文書】B NTS2026.xlsx';
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheet = wb.worksheets.getItem('原紙');
if (process.argv[2] === 'verify') {
  console.log((await wb.inspect({kind:'table',range:'10.21!B17:H17',include:'values,formulas',tableMaxRows:1,tableMaxCols:7,maxChars:1400})).ndjson);
  const p=await wb.render({sheetName:'10.21',range:'B2:H44',scale:1.5,format:'png'});
  await fs.writeFile('final.png',new Uint8Array(await p.arrayBuffer()));
} else if (process.argv[2] === 'inspect') {
  console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:1800})).ndjson);
  const p = await wb.render({sheetName:'原紙',range:'B2:H44',scale:1.5,format:'png'});
  await fs.writeFile('before.png',new Uint8Array(await p.arrayBuffer()));
} else {
  const edits = {G4:46316,C8:'AU-K261021-1',C9:'光都工場',C10:'生産技術部 幸田宛',B17:'4F9-P5132-M0E-DC24V',C17:'電磁弁用コイル',D17:'CKD',E17:5,B42:'備考：アマチュアコア修繕 部品'};
  for (const [cell,value] of Object.entries(edits)) sheet.getRange(cell).values=[[value]];
  sheet.getRange('F17').clear({applyTo:'contents'});
  wb.recalculate();
  const p=await wb.render({sheetName:'原紙',range:'B2:H44',scale:1.5,format:'png'});
  await fs.writeFile('after.png',new Uint8Array(await p.arrayBuffer()));
  console.log((await wb.inspect({kind:'table',range:'原紙!B17:H17',include:'values,formulas',tableMaxRows:1,tableMaxCols:7,maxChars:1400})).ndjson);
  await (await SpreadsheetFile.exportXlsx(wb)).save('authored.xlsx');
  await fs.writeFile('edits.json',JSON.stringify(edits,null,2));
}
