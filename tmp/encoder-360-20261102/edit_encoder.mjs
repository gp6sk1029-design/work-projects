import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';

const dir=new URL('./',import.meta.url);
const info=JSON.parse(await fs.readFile(new URL('inspection.json',dir),'utf8'));
const target=info.sheets.find(s=>s.name==='Sheet1');
const rows=target.E_all.filter(x=>x.row>=14);
if(rows.length!==360||!rows.every((x,i)=>x.row===14+10*i&&x.D===i+1))throw new Error('E列の360個の順番が想定と違います');
if(!target.F_sequence.every((x,i)=>x===i+1))throw new Error('F列の番号が1～360ではありません');
const started=Date.now();
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(info.source));
const sheet=wb.worksheets.getItem('Sheet1');
const mode=process.argv[2]??'inspect';
console.log(JSON.stringify({stage:'import',seconds:(Date.now()-started)/1000}));
if(mode==='edit'){
  sheet.getRange('G5:G364').formulas=rows.map(x=>['=E'+x.row]);
  sheet.getRange('G5:G364').setNumberFormat(target.G_first.find(c=>c.cell==='G5').format);
  wb.recalculate();
  const actual=sheet.getRange('G5:G364').values.flat();
  for(let i=0;i<360;i++){
    const expected=rows[i].cached;
    if(typeof actual[i]!=='number'||Math.abs(actual[i]-expected)>1e-9)throw new Error(`値不一致 G${i+5}`);
  }
  await (await SpreadsheetFile.exportXlsx(wb)).save(fileURLToPath(new URL('authored.xlsx',dir)));
  await fs.writeFile(new URL('authored-values.json',dir),JSON.stringify({values:actual,source:rows},null,2));
}
const preview=await wb.render({sheetName:'Sheet1',range:'B2:J22',scale:1.5,format:'png'});
await fs.writeFile(new URL(mode+'.png',dir),new Uint8Array(await preview.arrayBuffer()));
console.log(JSON.stringify({stage:'complete',mode,seconds:(Date.now()-started)/1000}));
