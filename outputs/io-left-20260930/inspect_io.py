import zipfile, xml.etree.ElementTree as ET, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

source=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\資料\_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260925A.xlsx')
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(source) as z:
    wb=ET.fromstring(z.read('xl/workbook.xml'))
    rel=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    targets={e.attrib['Id']:e.attrib['Target'] for e in rel}
    strings=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        strings=[''.join(t.text or '' for t in si.findall('s:t',ns)+si.findall('s:r/s:t',ns)) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    result={}
    for sh in wb.find('s:sheets',ns):
        target=targets[sh.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
        path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        cells={}
        tree=ET.fromstring(z.read(path))
        for c in tree.findall('.//s:sheetData/s:row/s:c',ns):
            v=c.find('s:v',ns)
            t=c.attrib.get('t')
            val=v.text if v is not None else None
            if t=='s' and val is not None: val=strings[int(val)]
            if t=='inlineStr':
                node=c.find('s:is',ns)
                val=''.join(t.text or '' for t in node.findall('s:t',ns)+node.findall('s:r/s:t',ns))
            if val is not None: cells[c.attrib['r']]=val
        result[sh.attrib['name']]={'path':path,'cells':cells,'merged':[m.attrib['ref'] for m in tree.findall('.//s:mergeCell',ns)]}
    Path(__file__).with_name('source_cells.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:{'cells':len(v['cells']),'path':v['path']} for k,v in result.items()},ensure_ascii=False))
    for k,v in result.items():
        if k=='IO':
            for address,value in v['cells'].items():
                if any(s in value for s in ['右','左','名称','コメント','ユニット']): print(address,repr(value))
