import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const dir = import.meta.dirname;
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(`${dir}/原紙バックアップ.xlsx`));
console.log((await wb.inspect({kind:'region',sheetId:'集計表',range:'B3:G4',maxChars:1500})).ndjson);
for (const phase of ['before','after']) {
  if (phase === 'after') {
    const s = wb.worksheets.getItem('集計表');
    s.getRange('C3').values = [['2717-2610A']];
    s.getRange('C4').values = [['インナー巻線機 (AIW-1100T) 〈2台〉【マーレOH】']];
    wb.recalculate();
  }
  try {
    const png = await wb.render({sheetName:'集計表',range:'B3:G4',scale:2,format:'png'});
    await fs.writeFile(`${dir}/${phase}.png`,new Uint8Array(await png.arrayBuffer()));
  } catch (e) {console.log('描画エラー',phase,String(e));}
}
console.log((await wb.inspect({kind:'region',sheetId:'集計表',range:'B3:G4',maxChars:1500})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save(`${dir}/candidate.xlsx`);
console.log('候補保存完了');
