"""D版を読み取り専用で調査する。"""
from pathlib import Path
import collections
import json
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261023D.smc2"))
with zipfile.ZipFile(source) as archive:
    print("ENTRIES", len(archive.namelist()))
    print("SUFFIXES", collections.Counter(Path(n).suffix for n in archive.namelist()))
    for name in archive.namelist():
        content = archive.read(name)
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue
        if "A(左側)" not in text and "B(右側)" not in text:
            continue
        print("\nENTRY", name, "length", len(text), "prefix", repr(text[:80]))
        if text.startswith("[SLWD"):
            rows = [line for line in text.splitlines() if "A(左側)" in line or "B(右側)" in line]
            print("SLWD", len(rows), *[r[:600] for r in rows[:2]], sep="\n")
        elif text.lstrip().startswith("{"):
            rows = []
            for line in text.splitlines():
                if "A(左側)" in line or "B(右側)" in line:
                    try:
                        obj = json.loads(line)
                        def walk(v, path=""):
                            if isinstance(v, dict):
                                for key, child in v.items(): walk(child, path + "/" + key)
                            elif isinstance(v, list):
                                for i, child in enumerate(v): walk(child, path + "/" + str(i))
                            elif isinstance(v, str) and ("A(左側)" in v or "B(右側)" in v):
                                rows.append((path, v))
                        walk(obj)
                    except json.JSONDecodeError:
                        rows.append(("UNPARSED", line[:500]))
            print("JSONPATHS", collections.Counter(p.split('/')[-1] for p, v in rows))
            print("SAMPLES", rows[:5])
        elif text.lstrip().startswith("<"):
            try:
                root = ET.fromstring(text)
                rows=[]
                for element in root.iter():
                    for key, value in element.attrib.items():
                        if "A(左側)" in value or "B(右側)" in value: rows.append((element.tag,key,value))
                    if element.text and ("A(左側)" in element.text or "B(右側)" in element.text):
                        rows.append((element.tag,"TEXT",element.text[:400]))
                print("XMLKEYS", collections.Counter((tag,key) for tag,key,v in rows))
                print("SAMPLES", rows[:5])
            except ET.ParseError:
                print("XML FAILED",text[:300])
        else:
            print("OTHER",[line[:350] for line in text.splitlines() if "A(左側)" in line or "B(右側)" in line][:5])
