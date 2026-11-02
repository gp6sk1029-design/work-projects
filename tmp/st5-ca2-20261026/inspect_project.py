"""現行B版のST1/ST5と関連ラダー・変数を読み取り専用で調査する。"""
from pathlib import Path
import collections
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
base=Path(__file__).resolve().parent
source=next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261026B.smc2"))
with zipfile.ZipFile(source) as z:
    texts={}
    for name in z.namelist():
        try:text=z.read(name).decode("utf-8-sig")
        except UnicodeError:continue
        if "\x00" not in text:texts[name]=text
    oem_name=next(n for n in texts if n.endswith(".oem"))
    root=ET.fromstring(texts[oem_name])
    entities={e.get("id"):e.attrib for e in root.iter("Entity")}
    parents={c:p for p in root.iter() for c in p}
    def nearest_entity(e):
        e=parents.get(e)
        while e is not None and e.tag!="Entity":e=parents.get(e)
        return e
    for e in root.iter("Entity"):
        if e.get("type")=="PouBody" or any(k in e.get("name","") for k in ("Movements","AutoMode","IO_","ModeManagement")):
            parent=nearest_entity(e)
            print("ENTITY",e.attrib,"PARENT",parent.attrib if parent is not None else None)
    global_name=next(n for n,t in texts.items() if t.startswith("[SLWD") and "+GN=VAR_GLOBAL" in t)
    rows=[]
    for line in texts[global_name].splitlines():
        if line.startswith("++"):
            row=dict(p.split("=",1) for p in line[2:].split("\t") if "=" in p);rows.append(row)
    for row in rows:
        if re.search(r"Ca[123]|Cv_Rdy|FH_|Pos_0[15]|Pause|Station_A_Data|Auto_A",row.get("N","")):
            small={k:v for k,v in row.items() if k!="EC"}
            print("GLOBAL",small)
    for name,text in texts.items():
        if text.startswith("[SLWD"):
            for line in text.splitlines():
                if any(k in line for k in ("N=ST1_A_Ca1","N=ST5_A_Ca2")):print("DECL",name,line)
        elif text.lstrip().startswith("{"):
            try:ladder=[json.loads(line) for line in text.splitlines() if line.strip()]
            except json.JSONDecodeError:continue
            for i,row in enumerate(ladder):
                if any(k in json.dumps(row) for k in ("ST1_A_Ca1","ST5_A_Ca2")):
                    print("RELATED",name,"NAME",entities.get(Path(name).stem,{}).get("name"),"ROW",i,json.dumps(row,ensure_ascii=False))
    result={"source":str(source),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "texts":texts,"entities":entities,"global_name":global_name,"oem_name":oem_name}
    (base/"inspection.json").write_text(json.dumps(result,ensure_ascii=False),encoding="utf-8")
