import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const dir=import.meta.dirname;
const m=JSON.parse(await fs.readFile(`${dir}/manifest.json`,'utf8'));
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(`${dir}/before.xlsx`));
const s=w.worksheets.getItem('電気部品');
for(const phase of ['before','after']){
 if(phase==='after'){
  s.getRange('B16:F21').values=m.items;
  for(let r=16;r<=21;r++) s.getRange(`G${r}`).formulas=[[`=E${r}*F${r}`]];
  s.getRange('G41').formulas=[['=SUM(G16:G40)']];
  s.getRange('G42').formulas=[['=G41++O41+W41+AE41+AM41+G87']];
  w.recalculate();
 }
 const im=await w.render({sheetName:'電気部品',range:'B15:H22',scale:1.8,format:'png'});
 await fs.writeFile(`${dir}/${phase}.png`,new Uint8Array(await im.arrayBuffer()));
}
console.log((await w.inspect({kind:'region',sheetId:'電気部品',range:'B16:G21',maxChars:2200})).ndjson);
console.log((await w.inspect({kind:'region',sheetId:'電気部品',range:'G41:G42',maxChars:600})).ndjson);
await(await SpreadsheetFile.exportXlsx(w)).save(`${dir}/candidate.xlsx`);
