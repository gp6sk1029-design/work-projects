import zipfile,xml.etree.ElementTree as ET,json,re,sys,hashlib,shutil
from pathlib import Path
from xml.sax.saxutils import escape
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).parent
source=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\資料\_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260925A.xlsx')
filename='_設備資料_3089-2603A_検査箱詰め装置_CORE_SUB__PIP-02F02NX__20260930A_左側更新.xlsx'
output=base/filename
destination=source.parent/filename
assert not output.exists() and not destination.exists(),'保存先に同名ファイルがあります'
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
changes=json.loads((base/'changes.json').read_text(encoding='utf-8'))
pairs=json.loads((base/'pairs.json').read_text(encoding='utf-8'))
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read_cells(z,path):
    strings=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        strings=[''.join(t.text or '' for t in si.findall('s:t',ns)+si.findall('s:r/s:t',ns)) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    tree=ET.fromstring(z.read(path)); cells={}
    for c in tree.findall('.//s:sheetData/s:row/s:c',ns):
        v=c.find('s:v',ns)
        text=v.text if v is not None else None
        if c.get('t')=='s' and text is not None: text=strings[int(text)]
        elif c.get('t')=='inlineStr':
            node=c.find('s:is',ns)
            text=''.join(t.text or '' for t in node.findall('s:t',ns)+node.findall('s:r/s:t',ns))
        cells[c.get('r')]={'value':text,'formula':ET.tostring(c.find('s:f',ns)) if c.find('s:f',ns) is not None else None,'style':c.get('s')}
    return cells
with zipfile.ZipFile(source) as original, zipfile.ZipFile(base/'artifact-edited.xlsx') as edited:
    authored=read_cells(edited,'xl/worksheets/sheet2.xml')
    xml=original.read('xl/worksheets/sheet2.xml').decode('utf-8')
    for change in changes:
        addr=change['target']; val=authored[addr]['value']
        assert val==change['after'],(addr,val,change['after'])
        pattern=rf'<c\b(?=[^>]*\br="{addr}")(?:[^>]*/>|[^>]*>.*?</c>)'
        def replace(match):
            original_cell=match.group()
            start=original_cell.split('>',1)[0].rstrip('/')
            start=re.sub(r'\s+t="[^"]*"','',start)
            return start+' t="inlineStr"><is><t xml:space="preserve">'+escape(val)+'</t></is></c>'
        xml,count=re.subn(pattern,replace,xml,count=1,flags=re.S)
        assert count==1,addr
    with zipfile.ZipFile(output,'w') as final:
        for entry in original.infolist():
            data=xml.encode('utf-8') if entry.filename=='xl/worksheets/sheet2.xml' else original.read(entry.filename)
            final.writestr(entry,data)
with zipfile.ZipFile(source) as original,zipfile.ZipFile(output) as final:
    assert final.testzip() is None
    assert original.namelist()==final.namelist()
    for entry in original.namelist():
        if entry!='xl/worksheets/sheet2.xml': assert original.read(entry)==final.read(entry),entry
    old=read_cells(original,'xl/worksheets/sheet2.xml'); new=read_cells(final,'xl/worksheets/sheet2.xml')
    targets={c['target'] for c in changes}
    diff=[]
    for address in set(old)|set(new):
        if old.get(address)!=new.get(address):
            diff.append(address)
            assert address in targets,address
        assert old[address]['formula']==new[address]['formula'],address
        assert old[address]['style']==new[address]['style'],address
    assert set(diff)==targets
    for pair in pairs: assert (new[pair['target']]['value'] or '')==pair['expected'],pair
    for c in changes:
        value=new[c['target']]['value']
        assert '右' not in value and re.search(r'(?<![A-Za-z0-9])R(?![A-Za-z0-9])',value) is None,c
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
shutil.copy2(output,destination)
assert hashlib.sha256(destination.read_bytes()).digest()==hashlib.sha256(output.read_bytes()).digest()
report={'file':str(destination),'changes':len(changes),'comments':sum(c['kind']=='コメント' for c in changes),'names':sum(c['kind']=='名称' for c in changes),'verified_pairs':len(pairs),'other_zip_parts_unchanged':True,'formulas_and_styles_unchanged':True,'source_sha256':source_hash}
(base/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
