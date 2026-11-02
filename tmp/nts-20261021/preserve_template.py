"""作成ツールのセル出力を使い、原紙の印刷設定を保持した新タブを追加する。"""
from pathlib import Path
from zipfile import ZipFile
import copy, hashlib, json, re, shutil, uuid
import xml.etree.ElementTree as ET

BASE=Path(__file__).parent
SRC=Path(r'\\nas-ime5\生産技術部\1.注文書\A【経費】 10万円以下 修理部品 消耗部品 等\A【注文書】B NTS2026.xlsx')
OUT=BASE/'completed.xlsx'
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
Q=lambda s:f'{{{NS}}}{s}'
ET.register_namespace('',NS)
assert not SRC.with_name('~$'+SRC.name).exists(), 'Excelが開いているため停止'
source_hash=hashlib.sha256(SRC.read_bytes()).hexdigest()
with ZipFile(SRC) as z:
    original={i.filename:z.read(i) for i in z.infolist()}
    infos=z.infolist()
    archive_comment=z.comment
wb=original['xl/workbook.xml'].decode('utf-8')
wr=ET.fromstring(wb)
assert all(s.get('name')!='10.21' for s in wr.find(Q('sheets')))
assert not any(b'AU-K261021-1' in v or b'4F9-P5132-M0E-DC24V' in v for v in original.values())
template='xl/worksheets/sheet11.xml'
newname='xl/worksheets/sheet12.xml'
assert newname not in original
edits=json.loads((BASE/'edits.json').read_text(encoding='utf-8'))
with ZipFile(BASE/'authored.xlsx') as az:
    aw=ET.fromstring(az.read('xl/workbook.xml'))
    a_sheet=next(s for s in aw.find(Q('sheets')) if s.get('name')=='原紙')
    ar=ET.fromstring(az.read('xl/_rels/workbook.xml.rels'))
    target=next(r.get('Target') for r in ar if r.get('Id')==a_sheet.get(f'{{{REL}}}id'))
    apath=target.lstrip('/') if target.startswith('/') else 'xl/'+target
    authored=ET.fromstring(az.read(apath))
    sst=[]
    if 'xl/sharedStrings.xml' in az.namelist():
        sst=[''.join(n.itertext()) for n in ET.fromstring(az.read('xl/sharedStrings.xml'))]
    values={c.get('r'):c for c in authored.iter(Q('c'))}

def authored_cell(address,old):
    c=values[address]
    typ=c.get('t')
    if typ=='s':
        value=sst[int(c.find(Q('v')).text)]
    elif typ=='inlineStr':
        value=''.join(c.find(Q('is')).itertext())
    elif typ=='str':
        value=c.find(Q('v')).text or ''
    else:
        value=float(c.find(Q('v')).text)
    assert value==edits[address], (address,value,edits[address])
    attrs=dict(ET.fromstring(old).attrib)
    attrs.pop('t',None)
    node=ET.Element(Q('c'),attrs)
    if isinstance(value,str):
        node.set('t','inlineStr')
        t=ET.SubElement(ET.SubElement(node,Q('is')),Q('t'))
        t.text=value
        t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
        result=ET.tostring(node,encoding='unicode')
        return result
    ET.SubElement(node,Q('v')).text=str(int(value))
    return ET.tostring(node,encoding='unicode')

newxml=original[template].decode('utf-8')
for address in edits:
    pattern=rf'<c\b(?=[^>]*\br="{address}")[^>]*?(?:/>|>.*?</c>)'
    newxml,count=re.subn(pattern,lambda m:authored_cell(address,m.group()),newxml,count=1)
    assert count==1,address
# 原紙の数式を保持し、ゼロ金額を印刷しない設定を維持する。
sv=ET.fromstring(newxml).find(Q('sheetViews'))
assert sv is not None
newxml=re.sub(r'<sheetView\b[^>]*>',lambda m:re.sub(r'\s+tabSelected="[^"]*"','',m.group())[:-1]+' tabSelected="1" showZeros="0">' if 'showZeros=' not in m.group() else re.sub(r'\s+tabSelected="[^"]*"','',m.group())[:-1]+' tabSelected="1">',newxml,count=1)
newxml=re.sub(r'codeName="[^"]*"','codeName="NTS1021"',newxml,count=1)
newxml=re.sub(r'xr:uid="[^"]*"','xr:uid="{'+str(uuid.uuid4()).upper()+'}"',newxml,count=1)
styles=original['xl/styles.xml'].decode('utf-8')
cx=re.search(r'<cellXfs\b[^>]*>(.*?)</cellXfs>',styles,re.S)
cxroot=ET.fromstring('<cellXfs xmlns="'+NS+'">'+cx.group(1)+'</cellXfs>')
b17=ET.fromstring(newxml).find('.//'+Q('c')+'[@r="B17"]')
xf=copy.deepcopy(list(cxroot)[int(b17.get('s','0'))])
align=xf.find(Q('alignment'))
if align is None: align=ET.SubElement(xf,Q('alignment'))
align.set('shrinkToFit','1')
xf.set('applyAlignment','1')
idx=len(cxroot)
styles=styles[:cx.start()]+re.sub(r'count="\d+"',f'count="{idx+1}"',cx.group(0),count=1).replace('</cellXfs>',ET.tostring(xf,encoding='unicode')+'</cellXfs>')+styles[cx.end():]
newxml=re.sub(r'(<c\b[^>]*r="B17"[^>]*\bs=")[^"]*(")',lambda m:m.group(1)+str(idx)+m.group(2),newxml,count=1)
assert ET.fromstring(newxml).find('.//'+Q('c')+'[@r="B17"]').get('s')==str(idx)

payload=original.copy()
# 新規タブを先頭へ追加。既存タブの選択状態以外は元のバイトを維持する。
sheet_id=max(int(s.get('sheetId')) for s in wr.find(Q('sheets')))+1
wb=wb.replace('<sheets>','<sheets><sheet name="10.21" sheetId="'+str(sheet_id)+'" r:id="rId16"/>',1)
wb=re.sub(r'<calcPr\b[^>]*/>','<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>',wb,count=1)
wb=re.sub(r'(<workbookView\b[^>]*)(/>)',lambda m:re.sub(r'\s+activeTab="[^"]*"','',m.group(1))+' activeTab="0"'+m.group(2),wb,count=1)
assert '<definedNames>' not in wb
wb=wb.replace('</sheets>','</sheets><definedNames><definedName name="_xlnm.Print_Area" localSheetId="0">\'10.21\'!$B$2:$H$44</definedName></definedNames>',1)
payload['xl/workbook.xml']=wb.encode('utf-8')
rels=original['xl/_rels/workbook.xml.rels'].decode('utf-8')
assert 'Id="rId16"' not in rels
payload['xl/_rels/workbook.xml.rels']=rels.replace('</Relationships>','<Relationship Id="rId16" Type="'+REL+'/worksheet" Target="worksheets/sheet12.xml"/></Relationships>').encode('utf-8')
ct=original['[Content_Types].xml'].decode('utf-8')
payload['[Content_Types].xml']=ct.replace('</Types>','<Override PartName="/xl/worksheets/sheet12.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>').encode('utf-8')
payload['xl/styles.xml']=styles.encode('utf-8')
for name in original:
    if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',name):
        payload[name]=original[name].replace(b'tabSelected="1"',b'tabSelected="0"')
payload[newname]=newxml.encode('utf-8')
payload['xl/worksheets/_rels/sheet12.xml.rels']=original['xl/worksheets/_rels/sheet11.xml.rels']
with ZipFile(OUT,'w') as zout:
    zout.comment=archive_comment
    for info in infos: zout.writestr(info,payload[info.filename])
    for name in payload.keys()-original.keys(): zout.writestr(name,payload[name])

# 保存結果を独立した読み取りライブラリで検証する。
import openpyxl
check=openpyxl.load_workbook(OUT,data_only=False)
assert check.sheetnames[0]=='10.21' and len(check.sheetnames)==12
sh=check['10.21']
for address,value in edits.items():
    if address=='G4': assert sh[address].value.date().isoformat()=='2026-10-21'
    else: assert sh[address].value==value,(address,sh[address].value,value)
assert sh['F17'].value is None and sh['G17'].value=='=E17*F17'
assert sh['G41'].value=='=SUM(G17:G40)'
assert sh.sheet_view.showZeros is False
assert str(sh.page_setup.paperSize)=='9' and sh.page_setup.orientation=='portrait'
assert sh['B17'].alignment.shrinkToFit is True
before=openpyxl.load_workbook(SRC,data_only=False)
for oldsheet in before:
    after=check[oldsheet.title]
    for row in oldsheet:
        for cell in row:
            other=after[cell.coordinate]
            assert cell.value==other.value,(oldsheet.title,cell.coordinate)
            for attr in ('font','fill','border','alignment','protection','number_format'):
                assert copy.copy(getattr(cell,attr))==copy.copy(getattr(other,attr)),(oldsheet.title,cell.coordinate,attr)
before.close(); check.close()
with ZipFile(OUT) as z: assert z.testzip() is None
assert not SRC.with_name('~$'+SRC.name).exists()
assert hashlib.sha256(SRC.read_bytes()).hexdigest()==source_hash
backup=BASE/'NTS2026_編集前.xlsx'
assert not backup.exists()
shutil.copy2(SRC,backup)
shutil.copyfile(OUT,SRC)
assert hashlib.sha256(SRC.read_bytes()).digest()==hashlib.sha256(OUT.read_bytes()).digest()
print('保存・照合完了：'+str(SRC))
print('新規タブ10.21、既存11タブのセル値・数式・書式は一致。数量5、価格未入力、A4縦、原紙保持。')
