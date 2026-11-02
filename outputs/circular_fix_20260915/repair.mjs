import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const dir='C:/Users/SEIGI-N13/work-projects/outputs/circular_fix_20260915';
const source='C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/資料/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260914A.xlsx';
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
console.log((await w.inspect({kind:'sheet',include:'id,name',maxChars:2000})).ndjson);
const name='箱詰めユニット センサ・シリンダ名称';
console.log((await w.inspect({kind:'region',sheetId:name,range:'O51:Z59',maxChars:2500})).ndjson);
const preview=await w.render({sheetName:name,range:'L49:AC61',scale:1.4,format:'png'});
await fs.writeFile(`${dir}/before.png`,new Uint8Array(await preview.arrayBuffer()));
if(process.argv.includes('--edit')){
  w.worksheets.getItem(name).getRange('T56').clear({applyTo:'contents'});
  w.recalculate();
  console.log('T56',w.worksheets.getItem(name).getRange('T56').values,w.worksheets.getItem(name).getRange('T56').formulas);
  const after=await w.render({sheetName:name,range:'L49:AC61',scale:1.4,format:'png'});
  await fs.writeFile(`${dir}/after.png`,new Uint8Array(await after.arrayBuffer()));
  await (await SpreadsheetFile.exportXlsx(w)).save(`${dir}/authored.xlsx`);
}
