import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = String.raw`C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\資料\_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260828A.xlsx`;
const outputDir = String.raw`C:\Users\SEIGI-N13\work-projects\outputs\io_comment_prefix_20260828`;
const finalPath = String.raw`C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\資料\_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260828A_IO線番コメント追記.xlsx`;

const mode = process.argv[2] ?? "inspect";
const inputPath = mode === "verify-final" ? finalPath : sourcePath;
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const colName = (index) => {
  let n = index + 1;
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
};
const starts = [0, 13, 26, 39, 52, 65, 78];
const rowGroups = [[6, 30, "X"], [32, 66, "Y"]];

function collectTargets(ioSheet) {
  const targets = [];
  let numericLineCount = 0;
  for (const [fromRow, toRow, prefix] of rowGroups) {
    for (const start of starts) {
      for (const [lineOffset, commentOffset] of [[6, 4], [9, 11]]) {
        if (start + commentOffset >= 89) continue;
        for (let row = fromRow; row < toRow; row++) {
          const lineCell = ioSheet.getCell(row, start + lineOffset);
          const commentCell = ioSheet.getCell(row, start + commentOffset);
          const line = lineCell.values?.[0]?.[0];
          const comment = commentCell.values?.[0]?.[0];
          if (typeof line !== "number" || !Number.isInteger(line)) continue;
          numericLineCount++;
          if (typeof comment !== "string" || comment.trim() === "") continue;
          targets.push({
            lineCell: `${colName(start + lineOffset)}${row + 1}`,
            commentCell: `${colName(start + commentOffset)}${row + 1}`,
            line: `${prefix}${line}`,
            comment,
          });
        }
      }
    }
  }
  return { targets, numericLineCount };
}

function formulaDigest(book) {
  const snapshot = [];
  for (const sheet of book.worksheets.items) {
    const used = sheet.getUsedRange();
    snapshot.push([sheet.name, used?.address ?? null, used?.formulas ?? null]);
  }
  return crypto.createHash("sha256").update(JSON.stringify(snapshot)).digest("hex");
}

if (mode === "inspect") {
  const sheets = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 10000 });
  console.log("SHEETS\n" + sheets.ndjson);
  const headers = await workbook.inspect({
    kind: "match",
    searchTerm: "線番|コメント",
    options: { useRegex: true, maxResults: 200 },
    summary: "IO header positions",
    maxChars: 20000,
  });
  console.log("HEADERS\n" + headers.ndjson);
  const ioSheet = workbook.worksheets.getItem("IO");
  const used = ioSheet.getUsedRange();
  console.log("USED_ADDRESS=" + used.address);
  const preview = await workbook.render({ sheetName: "IO", autoCrop: "all", scale: 0.6, format: "png" });
  await fs.writeFile(path.join(outputDir, "io_before.png"), new Uint8Array(await preview.arrayBuffer()));
  const { targets: candidates, numericLineCount } = collectTargets(ioSheet);
  console.log(`NUMERIC_LINE_COUNT=${numericLineCount}`);
  console.log(`NONEMPTY_COMMENT_CANDIDATE_COUNT=${candidates.length}`);
  console.log(JSON.stringify(candidates, null, 2));
  for (const range of ["A4:M15", "N4:Z15", "AA4:AM15", "AN4:AZ15", "BA4:BM15", "BN4:BZ15", "CA4:CK15", "A30:M41", "N30:Z41", "AA30:AM41", "AN30:AZ41", "BA30:BM41", "BN30:BZ41"]) {
    const table = await workbook.inspect({ kind: "table", range: `IO!${range}`, include: "values,formulas", tableMaxRows: 20, tableMaxCols: 20, maxChars: 8000 });
    console.log(`RANGE ${range}\n${table.ndjson}`);
  }
  process.exit(0);
}

if (mode === "edit") {
  const ioSheet = workbook.worksheets.getItem("IO");
  const beforeFormulaDigest = formulaDigest(workbook);
  const { targets, numericLineCount } = collectTargets(ioSheet);
  let changed = 0;
  let alreadyCorrect = 0;
  for (const item of targets) {
    const expectedPrefix = `【${item.line}】`;
    if (item.comment.startsWith(expectedPrefix)) {
      alreadyCorrect++;
      continue;
    }
    const withoutOldPrefix = item.comment.replace(/^【[XY][0-9]+】/, "");
    ioSheet.getRange(item.commentCell).values = [[`${expectedPrefix}${withoutOldPrefix}`]];
    changed++;
  }

  const afterFormulaDigest = formulaDigest(workbook);
  if (beforeFormulaDigest !== afterFormulaDigest) {
    throw new Error("コメント編集以外で数式が変更されました。");
  }

  const verify = collectTargets(ioSheet).targets;
  const mismatches = verify.filter((item) => !item.comment.startsWith(`【${item.line}】`));
  if (mismatches.length > 0) {
    throw new Error(`線番プレフィックス不一致: ${JSON.stringify(mismatches.slice(0, 10))}`);
  }

  const prefixMatch = await workbook.inspect({
    kind: "match",
    searchTerm: "^【[XY][0-9]+】",
    options: { useRegex: true, maxResults: 500 },
    summary: "IO comment prefixes",
    maxChars: 3000,
  });
  const errorScan = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "formula error scan",
    maxChars: 4000,
  });

  for (const sheet of workbook.worksheets.items) {
    const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 0.6, format: "png" });
    const safeName = sheet.name.replace(/[\\/:*?"<>|]/g, "_");
    await fs.writeFile(path.join(outputDir, `after_${safeName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }

  const tempOutput = path.join(outputDir, "edited_workbook.xlsx");
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(tempOutput);
  await fs.copyFile(tempOutput, finalPath);
  console.log(JSON.stringify({
    numericLineCount,
    targetCommentCount: targets.length,
    changed,
    alreadyCorrect,
    mismatches: mismatches.length,
    formulaDigestUnchanged: beforeFormulaDigest === afterFormulaDigest,
    prefixInspect: prefixMatch.ndjson,
    errorScan: errorScan.ndjson,
    tempOutput,
    finalPath,
  }, null, 2));
  process.exit(0);
}

if (mode === "verify-final") {
  const ioSheet = workbook.worksheets.getItem("IO");
  const { targets, numericLineCount } = collectTargets(ioSheet);
  const mismatches = targets.filter((item) => !item.comment.startsWith(`【${item.line}】`));
  const sourceBook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
  const formulaDigestUnchanged = formulaDigest(sourceBook) === formulaDigest(workbook);
  const samples = await workbook.inspect({
    kind: "table",
    range: "IO!A4:M18",
    include: "values,formulas",
    tableMaxRows: 20,
    tableMaxCols: 13,
    maxChars: 8000,
  });
  for (const [name, range] of [["io_input_sample", "A4:M24"], ["io_output_sample", "A30:M52"]]) {
    const preview = await workbook.render({ sheetName: "IO", range, scale: 1.5, format: "png" });
    await fs.writeFile(path.join(outputDir, `${name}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
  console.log(JSON.stringify({
    numericLineCount,
    targetCommentCount: targets.length,
    mismatches: mismatches.length,
    formulaDigestUnchanged,
    samples: samples.ndjson,
  }, null, 2));
  process.exit(mismatches.length === 0 && formulaDigestUnchanged ? 0 : 2);
}

throw new Error(`未対応モード: ${mode}`);
