import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const folder='C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/資料/RCON_Sysmac_IO貼付_6軸_20261017A';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(folder+'/RCON_6軸_ポジショナー1_Sysmac貼付.xlsx'));
for(const [sheet,filename] of [['OUT貼付','OUT_コピー用.tsv'],['IN貼付','IN_コピー用.tsv']]){
 const rows=wb.worksheets.getItem(sheet).getRange('A2:B33').values;
 const text=await fs.readFile(folder+'/'+filename,'utf8');
 const actual=text.replace(/\r\n/g,'\n').trimEnd().split('\n').map(r=>r.split('\t'));
 if(JSON.stringify(rows)!==JSON.stringify(actual))throw Error('TSVとExcelの不一致');
 const p=await wb.render({sheetName:sheet,range:'A15:E33',scale:1.3,format:'png'});
 await fs.writeFile(new URL(sheet==='OUT貼付'?'./out_lower.png':'./in_lower.png',import.meta.url),new Uint8Array(await p.arrayBuffer()));
}
const notes=await wb.render({sheetName:'OUT貼付',range:'G1:G23',scale:1.3,format:'png'});
await fs.writeFile(new URL('./instructions.png',import.meta.url),new Uint8Array(await notes.arrayBuffer()));
console.log(JSON.stringify({tsvMatchesWorkbook:true,rowsPerDirection:32,columnsPerDirection:2}));
