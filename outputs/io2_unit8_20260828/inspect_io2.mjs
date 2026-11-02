import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260826A.xlsx";
const outputDir = "C:/Users/SEIGI-N13/work-projects/outputs/io2_unit8_20260828";

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const sheets = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 6000 });
console.log("SHEETS");
console.log(sheets.ndjson);

for (const term of ["ユニット:", "OUT名称"]) {
  const result = await workbook.inspect({
    kind: "match",
    searchTerm: term,
    sheetId: "IO (2)",
    range: "A1:CA52",
    options: { useRegex: false, maxResults: 200 },
    summary: `IO(2) ${term}`,
  });
  console.log(`MATCH ${term}`);
  console.log(result.ndjson);
}

const sheet = workbook.worksheets.getItem("IO (2)");
function colName(index) {
  let n = index + 1;
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}
for (const row of [2, 3, 4, 5, 24, 25, 26, 27, 28, 29, 30, 31, 32]) {
  const vals = sheet.getRange(`A${row}:CA${row}`).values[0];
  const populated = [];
  for (let c = 0; c < vals.length; c += 1) {
    if (vals[c] !== null && vals[c] !== "") populated.push(`${colName(c)}${row}=${JSON.stringify(vals[c])}`);
  }
  console.log(`ROW ${row}`);
  console.log(populated.join(" | "));
}
console.log("UNIT8 AS:AT");
const unit8 = sheet.getRange("AS33:AT52").values;
for (let i = 0; i < unit8.length; i += 1) {
  console.log(`${33 + i}: ${JSON.stringify(unit8[i])}`);
}
console.log("OUTPUT UNIT LABELS");
for (const address of ["B33:C35", "N32:O34", "Z32:AA34", "AK32:AL34", "AV32:AW34", "BG32:BH34", "BR32:BS34"]) {
  console.log(address, JSON.stringify(sheet.getRange(address).values));
}
console.log("FIRST OUTPUT PAGE E:F and K:L");
for (let row = 33; row <= 52; row += 1) {
  console.log(`${row}: ${JSON.stringify(sheet.getRange(`E${row}:F${row}`).values[0])} | ${JSON.stringify(sheet.getRange(`K${row}:L${row}`).values[0])}`);
}
console.log("UNIT8 AB:AC and AH:AI");
for (let row = 33; row <= 52; row += 1) {
  console.log(`${row}: ${JSON.stringify(sheet.getRange(`AB${row}:AC${row}`).values[0])} | ${JSON.stringify(sheet.getRange(`AH${row}:AI${row}`).values[0])}`);
}

const preview = await workbook.render({
  sheetName: "IO (2)",
  range: "Y28:AI52",
  scale: 2,
  format: "png",
});
await fs.writeFile(`${outputDir}/io2_unit8_before.png`, new Uint8Array(await preview.arrayBuffer()));
