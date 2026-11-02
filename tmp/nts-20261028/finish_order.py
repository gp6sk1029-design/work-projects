"""作成ツールの出力を原紙へ限定反映し、既存タブを保持して検証・保存する。"""
from pathlib import Path
from zipfile import ZipFile
import copy, hashlib, json, posixpath, re, shutil, sys, uuid
import xml.etree.ElementTree as ET
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
REPORT=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
SRC=Path(REPORT['source'])
OUT=BASE.parent.parent/'outputs'/'nts-20261028'/'A【注文書】B NTS2026.xlsx'
TAB='10.28'
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
Q=lambda s:f'{{{NS}}}{s}'
ET.register_namespace('',NS)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert not SRC.with_name('~$'+SRC.name).exists(), 'Excelが開いているため停止'
assert digest(SRC)==REPORT['sha256'], '確認後に原本が変更されたため停止'
with ZipFile(SRC) as z:
    original={i.filename:z.read(i) for i in z.infolist()}
    infos=z.infolist(); archive_comment=z.comment
wb=original['xl/workbook.xml'].decode('utf-8')
wr=ET.fromstring(wb)
sheets=wr.find(Q('sheets'))
assert all(s.get('name')!=TAB for s in sheets)
rels=original['xl/_rels/workbook.xml.rels'].decode('utf-8')
rr=ET.fromstring(rels)
t=next(s for s in sheets if s.get('name')=='原紙')
target=next(r.get('Target') for r in rr if r.get('Id')==t.get(f'{{{REL}}}id'))
template=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
nextnum=max(int(re.search(r'sheet(\d+)\.xml$',n).group(1)) for n in original if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n))+1
newname=f'xl/worksheets/sheet{nextnum}.xml'
rid='rId'+str(max(int(r.get('Id')[3:]) for r in rr if re.fullmatch(r'rId\d+',r.get('Id')))+1)
edits=json.loads((BASE/'edits.json').read_text(encoding='utf-8'))
with ZipFile(BASE/'authored.xlsx') as az:
    aw=ET.fromstring(az.read('xl/workbook.xml'))
    ash=next(s for s in aw.find(Q('sheets')) if s.get('name')=='原紙')
    ar=ET.fromstring(az.read('xl/_rels/workbook.xml.rels'))
    at=next(r.get('Target') for r in ar if r.get('Id')==ash.get(f'{{{REL}}}id'))
    apath=at.lstrip('/') if at.startswith('/') else posixpath.normpath('xl/'+at)
    authored=ET.fromstring(az.read(apath))
    sst=[''.join(n.itertext()) for n in ET.fromstring(az.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in az.namelist() else []
    values={c.get('r'):c for c in authored.iter(Q('c'))}
    assert not any(c.get('t')=='e' for c in authored.iter(Q('c'))), '数式エラー'

def authored_cell(address,old):
    c=values[address]; typ=c.get('t')
    if typ=='s': value=sst[int(c.find(Q('v')).text)]
    elif typ=='inlineStr': value=''.join(c.find(Q('is')).itertext())
    elif typ=='str': value=c.find(Q('v')).text or ''
    else: value=float(c.find(Q('v')).text)
    assert value==edits[address], (address,value,edits[address])
    attrs=dict(ET.fromstring(old).attrib); attrs.pop('t',None)
    node=ET.Element(Q('c'),attrs)
    if isinstance(value,str):
        node.set('t','inlineStr')
        text=ET.SubElement(ET.SubElement(node,Q('is')),Q('t')); text.text=value
        text.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    else: ET.SubElement(node,Q('v')).text=str(int(value))
    return ET.tostring(node,encoding='unicode')

newxml=original[template].decode('utf-8')
for address in edits:
    pattern=rf'<c\b(?=[^>]*\br="{address}")[^>]*?(?:/>|>.*?</c>)'
    newxml,count=re.subn(pattern,lambda m:authored_cell(address,m.group()),newxml,count=1)
    assert count==1,address
def sheet_view(m):
    text=re.sub(r'\s+(tabSelected|showZeros)="[^"]*"','',m.group())
    return text[:-1]+' tabSelected="1" showZeros="0">'
newxml=re.sub(r'<sheetView\b[^>]*>',sheet_view,newxml,count=1)
newxml=re.sub(r'codeName="[^"]*"','codeName="NTS1028"',newxml,count=1)
newxml=re.sub(r'xr:uid="[^"]*"','xr:uid="{'+str(uuid.uuid4()).upper()+'}"',newxml,count=1)
# 型式のみ縮小表示を追加し、既存の書式定義は維持する。
styles=original['xl/styles.xml'].decode('utf-8')
cx=re.search(r'<cellXfs\b[^>]*>(.*?)</cellXfs>',styles,re.S)
cxroot=ET.fromstring('<cellXfs xmlns="'+NS+'">'+cx.group(1)+'</cellXfs>')
b17=ET.fromstring(newxml).find('.//'+Q('c')+'[@r="B17"]')
xf=copy.deepcopy(list(cxroot)[int(b17.get('s','0'))])
alignment=xf.find(Q('alignment'))
if alignment is None: alignment=ET.SubElement(xf,Q('alignment'))
alignment.set('shrinkToFit','1'); xf.set('applyAlignment','1')
idx=len(cxroot)
styles=styles[:cx.start()]+re.sub(r'count="\d+"',f'count="{idx+1}"',cx.group(0),count=1).replace('</cellXfs>',ET.tostring(xf,encoding='unicode')+'</cellXfs>')+styles[cx.end():]
newxml=re.sub(r'(<c\b[^>]*r="B17"[^>]*\bs=")[^"]*(")',lambda m:m.group(1)+str(idx)+m.group(2),newxml,count=1)
sheetid=max(int(s.get('sheetId')) for s in sheets)+1
wb=wb.replace('<sheets>',f'<sheets><sheet name="{TAB}" sheetId="{sheetid}" r:id="{rid}"/>',1)
wb=re.sub(r'<calcPr\b[^>]*/>','<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>',wb,count=1)
wb=re.sub(r'(<workbookView\b[^>]*)(/>)',lambda m:re.sub(r'\s+activeTab="[^"]*"','',m.group(1))+' activeTab="0"'+m.group(2),wb,count=1)
# 先頭挿入に伴い、既存シートに属する印刷範囲等の参照番号を繰り下げる。
wb=re.sub(r'localSheetId="(\d+)"',lambda m:f'localSheetId="{int(m.group(1))+1}"',wb)
defined=f'<definedName name="_xlnm.Print_Area" localSheetId="0">\'{TAB}\'!$B$2:$H$44</definedName>'
if '<definedNames>' in wb: wb=wb.replace('<definedNames>','<definedNames>'+defined,1)
else: wb=wb.replace('</sheets>','</sheets><definedNames>'+defined+'</definedNames>',1)
payload=original.copy()
payload['xl/workbook.xml']=wb.encode('utf-8')
payload['xl/_rels/workbook.xml.rels']=rels.replace('</Relationships>',f'<Relationship Id="{rid}" Type="{REL}/worksheet" Target="worksheets/sheet{nextnum}.xml"/></Relationships>').encode('utf-8')
ct=original['[Content_Types].xml'].decode('utf-8')
payload['[Content_Types].xml']=ct.replace('</Types>',f'<Override PartName="/{newname}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>').encode('utf-8')
payload['xl/styles.xml']=styles.encode('utf-8')
for name in original:
    if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',name): payload[name]=original[name].replace(b'tabSelected="1"',b'tabSelected="0"')
payload[newname]=newxml.encode('utf-8')
trels=posixpath.dirname(template)+'/_rels/'+posixpath.basename(template)+'.rels'
if trels in original: payload[f'xl/worksheets/_rels/sheet{nextnum}.xml.rels']=original[trels]
OUT.parent.mkdir(parents=True,exist_ok=True)
assert not OUT.exists()
with ZipFile(OUT,'w') as zout:
    zout.comment=archive_comment
    for info in infos: zout.writestr(info,payload[info.filename])
    for name in payload.keys()-original.keys(): zout.writestr(name,payload[name])
check=openpyxl.load_workbook(OUT,data_only=False)
assert check.sheetnames==[TAB]+REPORT['sheets']
sh=check[TAB]
for address,value in edits.items():
    if address=='G4': assert sh[address].value.date().isoformat()=='2026-10-28'
    else: assert sh[address].value==value,(address,sh[address].value,value)
assert sh['F17'].value is None and sh['G17'].value=='=E17*F17'
assert sh['G41'].value=='=SUM(G17:G40)'
assert sh['B42'].value=='備考：'
assert sh.sheet_view.showZeros is False
assert str(sh.page_setup.paperSize)=='9' and sh.page_setup.orientation=='portrait'
assert sh['B17'].alignment.shrinkToFit is True
assert '$B$2:$H$44' in str(sh.print_area)
before=openpyxl.load_workbook(SRC,data_only=False)
for old in before:
    after=check[old.title]
    assert str(old.print_area)==str(after.print_area),(old.title,'印刷範囲')
    for row in old:
        for cell in row:
            other=after[cell.coordinate]
            assert cell.value==other.value,(old.title,cell.coordinate)
            for attr in ('font','fill','border','alignment','protection','number_format'):
                assert copy.copy(getattr(cell,attr))==copy.copy(getattr(other,attr)),(old.title,cell.coordinate,attr)
before.close(); check.close()
with ZipFile(OUT) as z: assert z.testzip() is None
assert not SRC.with_name('~$'+SRC.name).exists()
assert digest(SRC)==REPORT['sha256']
backup=BASE/'NTS2026_編集前.xlsx'
assert not backup.exists()
shutil.copy2(SRC,backup)
shutil.copyfile(OUT,SRC)
assert digest(SRC)==digest(OUT)
print('保存・照合完了：'+str(SRC))
print('新規10.28、既存13タブ一致。AU-K261028-1、CKD 4GB210R-08-E00-1、数量3、価格空欄、光都工場／生産技術部 武田宛。')
print('印刷範囲 B2:H44、A4縦、ゼロ金額非表示、原紙保持。')
