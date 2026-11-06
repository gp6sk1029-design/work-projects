import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';

const dir = new URL('./', import.meta.url);
const mode = process.argv[2] ?? 'inspect';
const probeDir=process.env.CODEX_FREEZE_TEST_DIR;
const source = mode === 'probe' ? (probeDir ? `${probeDir}/freeze-source.xlsx` : new URL('freeze-source.xlsx', dir).pathname.replace(/^\/([A-Za-z]:)/,'$1')) : 'C:/Users/SEIGI-N13/Desktop/【業務報告2026 Ver2.7】幸田.xlsx';
const started = Date.now();
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheet = wb.worksheets.getItem('10月');
console.log(JSON.stringify({stage:'import',seconds:(Date.now()-started)/1000}));
if(mode === 'probe') {
  // 利用者の完成品には触れず、検証用コピーの空きセルだけを変更する。
  const cell=sheet.getRange('BS100');
  const before=cell.values;
  cell.values=[[123.456]];
  const exported=await SpreadsheetFile.exportXlsx(wb);
  await exported.save(probeDir ? `${probeDir}/freeze-test-only.xlsx` : new URL('freeze-test-only.xlsx',dir).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
  console.log(JSON.stringify({stage:'probe_saved',seconds:(Date.now()-started)/1000,cell:'BS100',before}));
  process.exit(0);
}
if(mode === 'edit') {
  const edits = JSON.parse(await fs.readFile(new URL('edits.json', dir), 'utf8'));
  for(const item of edits) sheet.getRange(item.cell).values = [[item.value]];
  // 計算確認用コピーで共有式を展開し、INDIRECTを同じ参照先の直接式へ変換する。
  // 最終ブックへは元の式をそのまま残し、入力値と検算済みキャッシュだけを反映する。
  const maps = JSON.parse(await fs.readFile(new URL('formula_map.json',dir),'utf8'));
  for(const [title, items] of Object.entries(maps)) {
    const ws = wb.worksheets.getItem(title);
    for(const item of items) ws.getRange(item.cell).formulas = [[item.formula]];
  }
  wb.recalculate();
  const exported = await SpreadsheetFile.exportXlsx(wb);
  await exported.save(new URL('artifact-edited.xlsx', dir).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
}
await fs.writeFile(new URL(`${mode}-checks.json`, dir), JSON.stringify({
  daily: sheet.getRange('E7:AI38').values,
  annual: wb.worksheets.getItem('年間集計').getRange('A1:AO98').values,
  totals: sheet.getRange('AJ8:AK38').values,
  status: sheet.getRange('AJ3').values,
  formulas: sheet.getRange('E17:AI17').formulas,
}, null, 2));
const preview = await wb.render({sheetName:'10月',range:'B5:AK38',scale:1,format:'png'});
await fs.writeFile(new URL(`${mode}.png`, dir), new Uint8Array(await preview.arrayBuffer()));
console.log(JSON.stringify({stage:'done',mode,seconds:(Date.now()-started)/1000}));
