import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';

const dir=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(dir,'template.xlsx')));
const sheet=wb.worksheets.getItem('原紙');
if(process.argv.includes('--inspect')) {
  console.log((await wb.inspect({kind:'sheet',include:'id,name'})).ndjson);
  const preview=await wb.render({sheetName:'原紙',range:'B1:G39',scale:1.5,format:'png'});
  await fs.writeFile(path.join(dir,'before.png'),new Uint8Array(await preview.arrayBuffer()));
} else {
  sheet.getRange('B6').values=[['依頼件名：巻線機オーバーホール新規制御部品']];
  sheet.getRange('C18').values=[['SLM-8000']];
  sheet.getRange('D18').values=[['制御機器(配線等を含む)']];
  sheet.getRange('F18').values=[[2]];
  sheet.getRange('G13').values=[['幸田']];
  // 長い依頼件名・品名は、該当欄のみ折返して表示する。
  sheet.getRange('B6:D6').format.wrapText=true;
  sheet.getRange('B6:D6').format.rowHeight=30;
  sheet.getRange('D18').format.wrapText=true;
  sheet.getRange('B18:G18').format.rowHeight=30;
  sheet.getRange('G13').format.horizontalAlignment='center';
  wb.recalculate();
  console.log((await wb.inspect({kind:'region',sheetId:'原紙',range:'B6:G18',maxChars:2000,tableMaxRows:13,tableMaxCols:6})).ndjson);
  console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:1500})).ndjson);
  const preview=await wb.render({sheetName:'原紙',range:'B1:G39',scale:1.5,format:'png'});
  await fs.writeFile(path.join(dir,'after.png'),new Uint8Array(await preview.arrayBuffer()));
  const outputDir='C:/Users/SEIGI-N13/work-projects/outputs/quote-20261019';
  await fs.mkdir(outputDir,{recursive:true});
  const outfile=path.join(outputDir,'【見積依頼書】_巻線機オーバーホール新規制御部品_SLM-8000_20261019.xlsx');
  const output=await SpreadsheetFile.exportXlsx(wb);
  await output.save(outfile);
  console.log(outfile);
}
