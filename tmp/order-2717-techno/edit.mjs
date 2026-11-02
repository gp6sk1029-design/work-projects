import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const d=import.meta.dirname,m=JSON.parse(await fs.readFile(`${d}/manifest.json`,'utf8'));
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(`${d}/before.xlsx`));
const s=w.worksheets.getItem('巻線');
for(const phase of ['before','after']){
 if(phase==='after'){
  for(const [a,v] of Object.entries(m.updates))s.getRange(a).values=[[v]];
  for(const a of ['G16','G17','G41','G42']){
   const f=s.getRange(a).formulas;
   s.getRange(a).formulas=f;
  }
  w.recalculate();
 }
 for(const [label,range]of [['head','B3:H11'],['items','B15:H18']]){
  const p=await w.render({sheetName:'巻線',range,scale:1.7,format:'png'});
  await fs.writeFile(`${d}/${phase}-${label}.png`,new Uint8Array(await p.arrayBuffer()));
 }
}
console.log((await w.inspect({kind:'region',sheetId:'巻線',range:'B16:G17',maxChars:1500})).ndjson);
await(await SpreadsheetFile.exportXlsx(w)).save(`${d}/candidate.xlsx`);
