"""F版の割付・ST・EtherCAT構成を読み取り専用で調査する。"""
from pathlib import Path
import collections
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
base = Path(__file__).resolve().parent
source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261023F.smc2"))
with zipfile.ZipFile(source) as z:
    texts = {}
    for name in z.namelist():
        raw = z.read(name)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeError:
            continue
        if "\x00" not in text:
            texts[name] = text
    oem_name = next(n for n in texts if n.endswith(".oem"))
    oem = ET.fromstring(texts[oem_name])
    names = {e.get("id"): e.get("name") for e in oem.iter("Entity")}
    for name, text in texts.items():
        if ("RCGW-ECT" in text or "112Byte" in text or "144Byte" in text or "ECAT://node#1/Out" in text) and not text.startswith("[SLWD"):
            print("CONFIG",name,len(text),repr(text[:140]))
            for match in list(re.finditer(r"RCGW-ECT|112Byte|144Byte|ECAT://node#1/Out",text))[:6]:
                print(text[max(0,match.start()-180):match.end()+260])
        if text.lstrip().startswith("{"):
            try: rows = [json.loads(l) for l in text.splitlines() if l.strip()]
            except json.JSONDecodeError: continue
            if not all(isinstance(r, dict) and "CLs" in r for r in rows): continue
            for ix,row in enumerate(rows):
                if "RCON1_RxRaw" in json.dumps(row):
                    print("RCON_LADDER",name,"NAME",names.get(Path(name).stem),"ROWS",len(rows))
                    break
            hits = []
            def walk(value, path=""):
                if isinstance(value, dict):
                    for k,v in value.items(): walk(v,path+"/"+k)
                elif isinstance(value,list):
                    for i,v in enumerate(value): walk(v,path+"/"+str(i))
                elif isinstance(value,str) and ("RCON1_RxRaw" in value or "E001_" in value):
                    hits.append((path,value))
            walk(rows)
            if hits:
                print("REFERENCES",name,[(p, v[:250]) for p,v in hits[:9]])
    globals_name = next(n for n,t in texts.items() if t.startswith("[SLWD") and "+GN=VAR_GLOBAL" in t)
    for line in texts[globals_name].splitlines():
        if line.startswith("++"):
            d=dict(x.split("=",1) for x in line[2:].split("\t") if "=" in x)
            if d.get("N","").startswith(("RCON1_","RCON2_")):
                print("GLOBAL",{k:d.get(k) for k in ("N","D","AT","Com")})
    (base/"inspection.json").write_text(json.dumps({"source":str(source),
        "sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"texts":texts,"names":names,
        "oem_name":oem_name,"globals_name":globals_name},ensure_ascii=False),encoding="utf-8")
