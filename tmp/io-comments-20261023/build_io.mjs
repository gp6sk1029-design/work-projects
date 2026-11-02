import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const base = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const revision = process.argv[2] ?? 'C';
if (!/^[A-Z]$/.test(revision)) throw new Error('版記号が不正です');
const data = JSON.parse(await fs.readFile(path.join(base, `io_data_${revision}.json`), 'utf8'));
const outputDir = path.resolve(base, `../../outputs/io-comments-20261023${revision}`);
await fs.mkdir(outputDir, { recursive: true });
const workbook = Workbook.create();

const configs = [
  ['X', '入力X', '#24476B', 'InputComments'],
  ['Y', '出力Y', '#67503A', 'OutputComments'],
];
if (data.unassigned.length) configs.push(['?', '未割付確認', '#805F19', 'UnassignedComments']);
for (const [prefix, name, color, tableName] of configs) {
  const records = prefix === '?' ? data.unassigned : data.rows.filter(r => r.io.startsWith(prefix));
  const sheet = workbook.worksheets.add(name);
  const last = records.length + 5;
  sheet.showGridLines = false;
  sheet.tabColor = color;
  sheet.getRange(`A1:D${last}`).format.font = { name: 'Arial', size: 11, color: '#202A35' };
  sheet.getRange(`A1:D${last}`).format.verticalAlignment = 'center';
  sheet.getRange(`A1:D${last}`).format.rowHeight = 23;
  sheet.getRange('A2').values = [[`I/Oコメント一覧 ${name}（${records.length}点）`]];
  sheet.getRange('A2').format.font = { name: 'Arial', size: 15, bold: true, color };
  sheet.getRange('A3').values = [[`出典：3089-2603A 検査箱詰め装置／20261023${revision}.smc2（保存済み）`]];
  sheet.getRange('A4').values = [[prefix === '?'
    ? '番号付き・割付先なしの変数。X400は割付済み変数にも同番号あり。内容は原文のまま。'
    : '割付済みX/Yのみ。未割付は別シート。未保存変更・内部変数・空き端子は対象外。A＝左、B＝右。']];
  sheet.getRange('A3:D4').format.font = { name: 'Arial', size: 10, color: '#596677' };
  sheet.getRange('A5:D5').values = [['I/O番号', '短いコメント', '変数名', '元のコメント']];
  sheet.getRange(`A6:D${last}`).values = records.map(r => [r.io, r.short, r.variable, r.original]);
  for (const [col, width] of [['A', 90], ['B', 350], ['C', 370], ['D', 540]]) {
    sheet.getRange(`${col}1:${col}${last}`).format.columnWidthPx = width;
  }
  sheet.getRange(`A5:A${last}`).setNumberFormat('@');
  sheet.getRange(`A6:D${last}`).format.wrapText = false;
  const table = sheet.tables.add(`A5:D${last}`, true, tableName);
  table.showFilterButton = true;
  sheet.getRange('A5:D5').format = { fill: color,
    font: { name: 'Arial', size: 11, bold: true, color: '#FFFFFF' },
    horizontalAlignment: 'center', verticalAlignment: 'center', rowHeight: 28 };
  sheet.freezePanes.freezeRows(5);
  sheet.freezePanes.freezeColumns(1);
  // 取り違えを防ぐため、全行の値を抽出元と照合する。
  const actual = sheet.getRange(`A6:D${last}`).values;
  const expected = records.map(r => [r.io, r.short, r.variable, r.original]);
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`${name}の照合不一致`);
}

workbook.recalculate();
console.log((await workbook.inspect({kind:'table', range:'入力X!A5:D10', include:'values',
  tableMaxRows:6, tableMaxCols:4, maxChars:1800})).ndjson);
console.log((await workbook.inspect({kind:'match', searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',
  options:{useRegex:true, maxResults:10}, maxChars:700})).ndjson);
for (const [, sheetName] of configs) {
  const preview = await workbook.render({sheetName, range:sheetName === '未割付確認' ? 'A1:D16' : 'A1:D19', scale:1, format:'png'});
  await fs.writeFile(path.join(base, `${revision}_${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  // 左右表記変更のある実データも表示確認できるようにする。
  if (sheetName !== '未割付確認') {
    const sample = await workbook.render({sheetName, range:'A20:D31', scale:1, format:'png'});
    await fs.writeFile(path.join(base, `${revision}_${sheetName}_左右.png`), new Uint8Array(await sample.arrayBuffer()));
  }
}
const output = await SpreadsheetFile.exportXlsx(workbook);
const file = path.join(outputDir, `I_Oコメント一覧_3089-2603A_20261023${revision}.xlsx`);
await output.save(file);
console.log(JSON.stringify({file, counts:data.counts}));
