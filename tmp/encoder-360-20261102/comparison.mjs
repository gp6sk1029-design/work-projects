import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const dir='C:/Users/SEIGI-N13/work-projects/tmp/encoder-360-20261102';
const info=JSON.parse(await fs.readFile(dir+'/comparison_inspection.json','utf8'));
const verify=process.argv.includes('--verify');
const file=verify?JSON.parse(await fs.readFile(dir+'/comparison_verification.json','utf8')).output:info.source;
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(file));
const sheet=wb.worksheets.getItem('Sheet1');
console.log((await wb.inspect({kind:'drawing',sheetId:'Sheet1',maxChars:3000})).ndjson);
console.log('charts',JSON.stringify(sheet.charts.items.map(c=>({id:c.id,title:c.title.text,type:c.type,series:c.series.items.map(s=>({name:s.name,formula:s.formula,categoryFormula:s.categoryFormula}))}))));
const before=await wb.render({sheetName:'Sheet1',range:'A1:N27',scale:1,format:'png'});
await fs.writeFile(dir+(verify?'/comparison_final.png':'/comparison_before.png'),new Uint8Array(await before.arrayBuffer()));
if(verify) {
 const series=sheet.charts.items[0].series.items;
 if(series.length!==2 || series[1].values.length!==360) throw new Error('保存後の系列点数不一致');
 for(let i=0;i<360;i++) if(Math.abs(series[1].values[i]-Number(info.G[i].value))>1e-12) throw new Error('保存後の比較値不一致 '+i);
 console.log('保存後の比較360点を再読込み照合済み');
}
if(process.argv.includes('--edit')) {
 const chart=sheet.charts.items[0];
 const xFormula="'グラフ作業用データ（1°毎）'!$A$4001:$A$4360";
 const added=chart.series.items[1];
 added.name='比較データ（G列）';
 added.categories=Array.from({length:360},(_,i)=>i);
 added.values=info.G.map(v=>Number(v.value));
 added.formula="'Sheet1'!$G$4:$G$363";
 added.categoryFormula=xFormula;
 added.line={fill:'#ED7D31',style:'solid',width:1.75};
 chart.legend={position:'bottom',textStyle:{fontSize:11}};
 wb.recalculate();
 if(added.values.length!==360) throw new Error('点数不一致');
 console.log('added',JSON.stringify({name:added.name,formula:added.formula,categoryFormula:added.categoryFormula,count:added.values.length}));
 const preview=await wb.render({sheetName:'Sheet1',range:'A1:N27',scale:1,format:'png'});
 await fs.writeFile(dir+'/comparison_authored.png',new Uint8Array(await preview.arrayBuffer()));
 await (await SpreadsheetFile.exportXlsx(wb)).save(dir+'/comparison_authored.xlsx');
}
