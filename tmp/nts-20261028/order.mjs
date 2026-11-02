import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';

// 原紙を読み込み、編集内容は別ファイルへ出力する。
const source = '\\\\nas-ime5\\生産技術部\\1.注文書\\A【経費】 10万円以下 修理部品 消耗部品 等\\A【注文書】B NTS2026.xlsx';
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheet = wb.worksheets.getItem('原紙');
if (process.argv[2] === 'inspect') {
  const p = await wb.render({sheetName:'原紙',range:'B2:H44',scale:1.5,format:'png'});
  await fs.writeFile('before.png',new Uint8Array(await p.arrayBuffer()));
} else {
  const edits={G4:46323,C8:'AU-K261028-1',C9:'光都工場',C10:'生産技術部 武田宛',B17:'4GB210R-08-E00-1',C17:'電磁弁',D17:'CKD',E17:3};
  for (const [cell,value] of Object.entries(edits)) sheet.getRange(cell).values=[[value]];
  sheet.getRange('F17').clear({applyTo:'contents'});
  wb.recalculate();
  const p=await wb.render({sheetName:'原紙',range:'B2:H44',scale:1.5,format:'png'});
  await fs.writeFile('after.png',new Uint8Array(await p.arrayBuffer()));
  console.log((await wb.inspect({kind:'table',range:'原紙!B17:H17',include:'values,formulas',tableMaxRows:1,tableMaxCols:7,maxChars:1400})).ndjson);
  await (await SpreadsheetFile.exportXlsx(wb)).save('authored.xlsx');
  await fs.writeFile('edits.json',JSON.stringify(edits,null,2));
}
