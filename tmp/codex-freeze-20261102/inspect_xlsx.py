"""元ブックを変更せず、フリーズ要因になり得る構造だけを集計する。"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import posixpath
import re
import time
import zipfile
import xml.etree.ElementTree as ET

p = Path(r"C:\Users\SEIGI-N13\Desktop\【業務報告2026 Ver2.7】幸田.xlsx")
start = time.perf_counter()
ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
out = {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
with zipfile.ZipFile(p) as z:
    out["zip_error"] = z.testzip()
    out["expanded_bytes"] = sum(e.file_size for e in z.infolist())
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    out["calculation"] = dict(wb.find("m:calcPr", ns).attrib) if wb.find("m:calcPr", ns) is not None else {}
    rel = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    targets = {r.get("Id"): posixpath.normpath(posixpath.join("xl", r.get("Target"))).lstrip("/") if not r.get("Target", "").startswith("/") else r.get("Target").lstrip("/") for r in rel}
    sheets = []
    functions = Counter()
    for s in wb.find("m:sheets", ns):
        rid = s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        path = targets[rid]
        root = ET.fromstring(z.read(path))
        formulas = root.findall(".//m:c/m:f", ns)
        direct_self = []
        for cell in root.findall(".//m:c", ns):
            f = cell.find("m:f", ns)
            if f is None:
                continue
            txt = f.text or ""
            functions.update(re.findall(r"([A-Za-z_][A-Za-z0-9_.]*)\s*\(", txt))
            if re.search(r"(?<![A-Za-z0-9_!])\$?" + re.sub(r"([A-Z]+)([0-9]+)", r"\1\$?\2", cell.get("r", "")) + r"(?![0-9])", txt):
                direct_self.append({"cell": cell.get("r"), "type": f.get("t"), "formula": txt[:180]})
        dim = root.find("m:dimension", ns)
        sheets.append({"name": s.get("name"), "state": s.get("state", "visible"), "xml_bytes": z.getinfo(path).file_size, "dimension": dim.get("ref") if dim is not None else None, "cells": len(root.findall(".//m:c", ns)), "rows": len(root.findall(".//m:row", ns)), "formulas": len(formulas), "array_formulas": sum(f.get("t") == "array" for f in formulas), "merges": len(root.findall(".//m:mergeCell", ns)), "conditional_formats": len(root.findall(".//m:conditionalFormatting", ns)), "self_reference_candidates": direct_self[:12]})
    out["sheets"] = sheets
    out["functions"] = functions.most_common(25)
    out["external_links"] = [n for n in z.namelist() if n.startswith("xl/externalLinks/") and n.endswith(".xml")]
    out["media_count"] = len([n for n in z.namelist() if n.startswith("xl/media/")])
    out["drawing_count"] = len([n for n in z.namelist() if n.startswith("xl/drawings/") and n.endswith(".xml")])
    if "xl/styles.xml" in z.namelist():
        styles = ET.fromstring(z.read("xl/styles.xml"))
        out["styles"] = {x.tag.split("}")[-1]: len(x) for x in styles}
    out["defined_names"] = [{"name": x.get("name"), "length": len(x.text or ""), "ref_error": "#REF!" in (x.text or "")} for x in wb.findall("m:definedNames/m:definedName", ns)]
out["inspection_seconds"] = round(time.perf_counter() - start, 3)
dest = Path(__file__).with_name("workbook_structure.json")
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
