import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';
const dir=import.meta.dirname;
const source='C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/資料/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260925A.xlsx';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:2000})).ndjson);
const mode=process.argv[2]||'inspect';
if(mode==='inspect') {
 const preview=await wb.render({sheetName:'IO',range:'AQ6:BL14',scale:1.4,format:'png'});
 await fs.writeFile(dir+'/before.png',new Uint8Array(await preview.arrayBuffer()));
 console.log('PREVIEW_OK');
} else {
 const changes=JSON.parse(await fs.readFile(dir+'/changes.json','utf8'));
 const sheet=wb.worksheets.getItem('IO');
 for(const change of changes) {
  if((sheet.getRange(change.target).values[0][0]??'')!==change.before) throw new Error('SOURCE_MISMATCH '+change.target);
  sheet.getRange(change.target).values=[[change.after]];
 }
 wb.recalculate();
 const preview=await wb.render({sheetName:'IO',range:'AQ6:BL14',scale:1.4,format:'png'});
 await fs.writeFile(dir+'/after.png',new Uint8Array(await preview.arrayBuffer()));
 await (await SpreadsheetFile.exportXlsx(wb)).save(dir+'/artifact-edited.xlsx');
 console.log('EDITED',changes.length);
}
