import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260826A.xlsx";
const outputPath = "C:/Users/SEIGI-N13/work-projects/outputs/io2_unit8_20260828/_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260826A_ユニット8左仕様.xlsx";

const source = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const edited = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));

const valueDiffs = [];
const formulaDiffs = [];

for (let s = 0; s < source.worksheets.getSheetCount(); s += 1) {
  const a = source.worksheets.getItemAt(s);
  const b = edited.worksheets.getItem(a.name);
  const rangeA = a.getUsedRange();
  const rangeB = b.getUsedRange();
  const va = rangeA.values;
  const vb = rangeB.values;
  const fa = rangeA.formulas;
  const fb = rangeB.formulas;
  const rows = Math.max(va.length, vb.length, fa.length, fb.length);
  const cols = Math.max(...va.map(r => r.length), ...vb.map(r => r.length), ...fa.map(r => r.length), ...fb.map(r => r.length));

  function colName(index) {
    let n = index + 1;
    let text = "";
    while (n > 0) {
      const rem = (n - 1) % 26;
      text = String.fromCharCode(65 + rem) + text;
      n = Math.floor((n - 1) / 26);
    }
    return text;
  }

  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      const formulaA = fa[r]?.[c] ?? null;
      const formulaB = fb[r]?.[c] ?? null;
      const address = `${colName(c)}${r + 1}`;
      if (formulaA !== formulaB) {
        formulaDiffs.push({ sheet: a.name, address, before: formulaA, after: formulaB });
        continue;
      }
      if (formulaA) continue;
      const valueA = va[r]?.[c] ?? null;
      const valueB = vb[r]?.[c] ?? null;
      if (valueA !== valueB) valueDiffs.push({ sheet: a.name, address, before: valueA, after: valueB });
    }
  }
}

const io = edited.worksheets.getItem("IO (2)");
const remainingRight = [];
for (let row = 33; row <= 52; row += 1) {
  for (const col of ["AB", "AI"]) {
    const value = io.getRange(`${col}${row}`).values[0][0];
    if (typeof value === "string" && value.includes("右")) remainingRight.push(`${col}${row}:${value}`);
  }
  for (const col of ["AC", "AH"]) {
    const value = io.getRange(`${col}${row}`).values[0][0];
    if (typeof value === "string" && /(^|_)R(?=_|$)/.test(value)) remainingRight.push(`${col}${row}:${value}`);
  }
}

console.log(JSON.stringify({
  valueDiffCount: valueDiffs.length,
  formulaDiffCount: formulaDiffs.length,
  remainingRightCount: remainingRight.length,
  valueDiffs,
  formulaDiffs,
  remainingRight,
}, null, 2));
