import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260826A.xlsx";
const outputDir = "C:/Users/SEIGI-N13/work-projects/outputs/io2_unit8_20260828";
const outputPath = `${outputDir}/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260826A_ユニット8左仕様.xlsx`;

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheet = workbook.worksheets.getItem("IO (2)");

const changes = [];

function updateCell(address, transform) {
  const cell = sheet.getRange(address);
  const before = cell.values[0][0];
  if (typeof before !== "string" || before.length === 0) return;
  const after = transform(before);
  if (after === before) return;
  cell.values = [[after]];
  changes.push({ address, before, after });
}

for (let row = 33; row <= 52; row += 1) {
  updateCell(`AB${row}`, value => value.replaceAll("右", "左"));
  updateCell(`AI${row}`, value => value.replaceAll("右", "左"));
  updateCell(`AC${row}`, value => value.replace(/(^|_)R(?=_|$)/g, "$1L"));
  updateCell(`AH${row}`, value => value.replace(/(^|_)R(?=_|$)/g, "$1L"));
}

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const check = await workbook.inspect({
  kind: "table",
  sheetId: "IO (2)",
  range: "Y28:AI52",
  include: "values,formulas",
  maxChars: 12000,
  tableMaxRows: 25,
  tableMaxCols: 11,
  tableMaxCellChars: 100,
});

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  sheetId: "IO (2)",
  range: "Y28:AI52",
  options: { useRegex: true, maxResults: 100 },
  summary: "ユニット8数式エラーチェック",
});

const preview = await workbook.render({
  sheetName: "IO (2)",
  range: "Y28:AI52",
  scale: 2,
  format: "png",
});
await fs.writeFile(`${outputDir}/io2_unit8_after.png`, new Uint8Array(await preview.arrayBuffer()));

console.log(JSON.stringify({ outputPath, changeCount: changes.length, changes }, null, 2));
console.log("CHECK");
console.log(check.ndjson);
console.log("ERRORS");
console.log(errors.ndjson);
