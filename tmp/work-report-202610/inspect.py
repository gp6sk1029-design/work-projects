"""業務報告の入力位置と既存値を読取り専用で確認する。"""
from pathlib import Path
from collections import Counter
import json
import zipfile
import xml.etree.ElementTree as E

p=Path(r"C:\Users\SEIGI-N13\Desktop\【業務報告2026 Ver2.7】幸田.xlsx")
ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
with zipfile.ZipFile(p) as z:
    strings=[]
    if "xl/sharedStrings.xml" in z.namelist():
        strings=["".join(e.itertext()) for e in E.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si",ns)]
    wb=E.fromstring(z.read("xl/workbook.xml"))
    rel={e.get("Id"):e.get("Target").lstrip("/") for e in E.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    sheet=next(s for s in wb.find("m:sheets",ns) if s.get("name")=="10月")
    target=rel[sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")]
    if not target.startswith("xl/"):target="xl/"+target
    root=E.fromstring(z.read(target))
    data=[]
    for row in root.findall("m:sheetData/m:row",ns):
        cells=[]
        for c in row:
            a=c.get("r"); v=c.find("m:v",ns);f=c.find("m:f",ns)
            value=v.text if v is not None else ""
            if c.get("t")=="s" and value:value=strings[int(value)]
            if c.get("t")=="inlineStr":value="".join(c.find("m:is",ns).itertext())
            if value or f is not None:
                cells.append({"cell":a,"value":value,"formula":f.text if f is not None else None,"fattr":f.attrib if f is not None else None,"style":c.get("s")})
        data.append({"row":row.get("r"),"cells":cells})
    result={"sheet_path":target,"sheet_id":sheet.get("sheetId"),"rows":data,"conditional_formats":[E.tostring(x,encoding="unicode") for x in root.findall("m:conditionalFormatting",ns)],"defined_names":[{"name":x.get("name"),"value":x.text} for x in wb.findall("m:definedNames/m:definedName",ns)],"sheet_views":[E.tostring(x,encoding="unicode") for x in root.findall("m:sheetViews",ns)]}
    Path(__file__).with_name("before.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"sheet_path":target,"rows":[{"row":r["row"],"cells":{c["cell"]:c["value"] for c in r["cells"] if c["cell"].rstrip("0123456789") in ("B","C","D","AJ","AK") or (c["formula"] is None and c["fattr"] is None and (len(c["cell"].rstrip("0123456789"))==1 or c["cell"].rstrip("0123456789")<="AI"))}} for r in data if 7<=int(r["row"])<=39]},ensure_ascii=False))
