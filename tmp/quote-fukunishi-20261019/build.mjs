import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';

const work='C:/Users/SEIGI-N13/work-projects/tmp/quote-fukunishi-20261019';
const outputDir='C:/Users/SEIGI-N13/work-projects/outputs/quote-fukunishi-20261019';
const filename='【見積依頼書】_巻線機オーバーホール_サーボモータ・アンプ_福西電機_20261019.xlsx';
const template='C:/Users/SEIGI-N13/Desktop/巻線機オーバーホール_福西電機見積依頼_20261019/変更前_リード線仕様/'+filename;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(template));
const sheet=wb.worksheets.getItem('原紙');
if(process.argv.includes('--before')){
  const png=await wb.render({sheetName:'原紙',range:'B1:G39',scale:1.4,format:'png'});
  await fs.writeFile(path.join(work,'before_connector.png'),new Uint8Array(await png.arrayBuffer()));
  process.exit(0);
}
const edits={
  C20:'MSMF022L1A1',
  C22:'MSMF042L1B1',
};
for(const [address,value] of Object.entries(edits))sheet.getRange(address).values=[[value]];
wb.recalculate();
console.log((await wb.inspect({kind:'region',sheetId:'原紙',range:'C18:G23',maxChars:2200,tableMaxRows:6,tableMaxCols:5})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:1000})).ndjson);
const png=await wb.render({sheetName:'原紙',range:'B1:G39',scale:1.4,format:'png'});
await fs.writeFile(path.join(work,'after.png'),new Uint8Array(await png.arrayBuffer()));
await fs.mkdir(outputDir,{recursive:true});
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(path.join(outputDir,filename));
await fs.writeFile(path.join(work,'edits.json'),JSON.stringify({edits,filename},null,2));
console.log(path.join(outputDir,filename));
