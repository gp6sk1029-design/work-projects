"""利用者更新済みE版のRCON1軸別テンプレートを読取り調査する。"""
from pathlib import Path
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
base = Path(__file__).resolve().parent
source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261026E.smc2"))
texts = {}
with zipfile.ZipFile(source) as z:
    for name in z.namelist():
        try:
            text = z.read(name).decode("utf-8-sig")
        except UnicodeError:
            continue
        if "\x00" not in text:
            texts[name] = text
oem_name = next(n for n in texts if n.endswith(".oem"))
entities = {e.get("id"): e.attrib for e in ET.fromstring(texts[oem_name]).iter("Entity")}
global_name = next(n for n, t in texts.items() if t.startswith("[SLWD") and "+GN=VAR_GLOBAL" in t)
for n, t in texts.items():
    if t.startswith("[SLWD"):
        lines = [l for l in t.splitlines() if re.search(r"\bN=(?:RCON1_[1-6](?:_|\t|$)|HMI_RCON1_[1-6](?:_|\t|$))", l)]
        if lines:
            print("TABLE", n, "\n" + "\n".join(lines))
    elif t.lstrip().startswith("{"):
        try:
            rows = [json.loads(l) for l in t.splitlines() if l.strip()]
        except json.JSONDecodeError:
            continue
        if n.endswith("7b1666c7-ee97-4210-81b2-fed5a6172074.xml"):
            print("RCON_SECTION", n, len(rows))
            for i, row in enumerate(rows):
                txts = [node.get("TXT", "") for node in row["CLs"] if node.get("__type") == "IST"]
                print("RCON_ROW", i, row.get("CMT", ""), "IST=" + str(len(txts)))
                if txts:
                    for txt in txts:
                        print("ST_HEAD", txt[:350])
                else:
                    print(json.dumps(row, ensure_ascii=False))
        else:
            for i, row in enumerate(rows):
                if "RCON1_1_" in json.dumps(row):
                    print("RELATED", entities.get(Path(n).stem, {}).get("name", n), i,
                          re.findall(r'"Var":"([^"]*)"', json.dumps(row, separators=(",", ":"))))
result = {"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "texts": texts, "entities": entities, "oem_name": oem_name, "global_name": global_name}
(base / "inspection.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
print("SOURCE_SHA256", result["source_sha256"])
