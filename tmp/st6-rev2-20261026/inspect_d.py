"""現行D版のST4/ST6と関連宣言・参照を読取り調査する。"""
from pathlib import Path
import json
import re
import zipfile
import hashlib
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
base = Path(__file__).resolve().parent
source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261026D.smc2"))
texts = {}
with zipfile.ZipFile(source) as z:
    for name in z.namelist():
        try:
            text = z.read(name).decode("utf-8-sig")
        except UnicodeError:
            continue
        if "\x00" not in text:
            texts[name] = text
oem = next(n for n in texts if n.endswith(".oem"))
root = ET.fromstring(texts[oem])
entities = {e.get("id"): e.attrib for e in root.iter("Entity")}
for e in entities.values():
    if e.get("type") == "PouBody":
        print("SECTION", e)
globals_name = next(n for n, t in texts.items() if t.startswith("[SLWD") and "+GN=VAR_GLOBAL" in t)
for n, text in texts.items():
    if text.startswith("[SLWD"):
        for line in text.splitlines():
            if re.search(r"\bN=(?:ST4_A_Rev1|ST6_A_Rev2|Stm_A_Rev|Out_CYw_Rev|Out_CYw_Swv|TimerQ_In_.*Rev|TimerQ_In_.*Swv|Out_CYS_Pos_0[46]|TimerQ_In_Sen_Work_A_Pos_0[46])", line):
                print("DECL", n, line)
    elif text.lstrip().startswith("{"):
        try:
            rows = [json.loads(l) for l in text.splitlines() if l.strip()]
        except json.JSONDecodeError:
            continue
        for i, row in enumerate(rows):
            s = json.dumps(row)
            if any(v in s for v in ("ST4_A_Rev1", "ST6_A_Rev2")):
                print("ROW", n, i, json.dumps(row, ensure_ascii=False))
result = {"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "texts": texts,
          "entities": entities, "global_name": globals_name, "oem_name": oem}
(base / "inspection.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
print("SOURCE_SHA256", result["source_sha256"])
