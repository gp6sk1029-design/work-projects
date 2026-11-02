import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(`${import.meta.dirname}/before.xlsx`));
console.log(w.help('range.format',{search:'shrinkToFit|shrink',include:'index,notes,examples',maxChars:2500}).ndjson);
