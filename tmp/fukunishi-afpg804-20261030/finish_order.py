"""Artifact入力だけを原紙コピーへ反映し、既存4タブを保持して保存する。"""
from pathlib import Path
from zipfile import ZipFile
import copy,hashlib,json,posixpath,re,shutil,sys,uuid
import xml.etree.ElementTree as E
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
B=Path(__file__).resolve().parent
info=json.loads((B/'inspection.json').read_text(encoding='utf-8'))
S=Path(info['source']);BACK=B/'福西電機2026_編集前.xlsx'
OUT=B.parent.parent/'outputs'/'fukunishi-afpg804-20261030'/S.name
TAB='10.30';NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main';REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
Q=lambda x:'{'+NS+'}'+x
E.register_namespace('',NS)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not S.with_name('~$'+S.name).exists(),'対象ブックが開かれています'
assert sha(S)==sha(BACK)==info['sha256'],'原本またはバックアップが変更されています'
with ZipFile(S) as z:
 old={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
wxml=old['xl/workbook.xml'].decode('utf-8');w=E.fromstring(wxml);sheets=w.find(Q('sheets'))
assert TAB not in [s.get('name') for s in sheets]
rels=old['xl/_rels/workbook.xml.rels'].decode('utf-8');rr=E.fromstring(rels)
def sheet_path(s,relations):
 t=next(x.get('Target') for x in relations if x.get('Id')==s.get('{'+REL+'}id'))
 return t.lstrip('/') if t.startswith('/') else posixpath.normpath('xl/'+t)
template=sheet_path(next(s for s in sheets if s.get('name')=='原紙'),rr)
newnum=max(int(re.search(r'sheet(\d+)\.xml$',n)[1]) for n in old if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n))+1
newpath=f'xl/worksheets/sheet{newnum}.xml'
rid='rId'+str(max(int(x.get('Id')[3:]) for x in rr if re.fullmatch(r'rId\d+',x.get('Id')))+1)
edits=json.loads((B/'edits.json').read_text(encoding='utf-8'))
with ZipFile(B/'authored.xlsx') as z:
 aw=E.fromstring(z.read('xl/workbook.xml'));ar=E.fromstring(z.read('xl/_rels/workbook.xml.rels'))
 ash=next(s for s in aw.find(Q('sheets')) if s.get('name')=='原紙')
 ax=E.fromstring(z.read(sheet_path(ash,ar)))
 sst=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
 cells={c.get('r'):c for c in ax.iter(Q('c'))}
 assert not any(c.get('t')=='e' for c in cells.values())
def authored_value(addr):
 c=cells[addr];t=c.get('t')
 if t=='s':return sst[int(c.find(Q('v')).text)]
 if t=='inlineStr':return ''.join(c.find(Q('is')).itertext())
 if t=='str':return c.find(Q('v')).text or ''
 return float(c.find(Q('v')).text)
assert authored_value('G17')==authored_value('G41')==10*1050==10500
nx=old[template].decode('utf-8')
for addr,expected in edits.items():
 val=authored_value(addr);assert val==expected,(addr,val,expected)
 def cell(m):
  node=E.fromstring(m[0]);attrs=dict(node.attrib);attrs.pop('t',None);new=E.Element(Q('c'),attrs)
  if isinstance(val,str):
   new.set('t','inlineStr');txt=E.SubElement(E.SubElement(new,Q('is')),Q('t'));txt.text=val
   txt.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
  else:E.SubElement(new,Q('v')).text=str(int(val))
  return E.tostring(new,encoding='unicode')
 nx,count=re.subn(rf'<c\b(?=[^>]*\br="{addr}")[^>]*?(?:/>|>.*?</c>)',cell,nx,count=1)
 assert count==1,addr
# 既存の金額計算式は保持してキャッシュ値だけ更新する。
for addr in ('G17','G41'):
 def cache(m):
  node=E.fromstring(m[0])
  node.attrib.pop('t',None)
  for child in list(node):
   if child.tag.rsplit('}',1)[-1]=='v':node.remove(child)
  v=E.SubElement(node,Q('v'))
  v.text='10500';return E.tostring(node,encoding='unicode')
 nx,count=re.subn(rf'<c\b(?=[^>]*\br="{addr}")[^>]*>.*?</c>',cache,nx,count=1)
 assert count==1
nx=re.sub(r'<sheetView\b[^>]*>',lambda m:re.sub(r'\s+(tabSelected|showZeros)="[^"]*"','',m[0])[:-1]+' tabSelected="1" showZeros="0">',nx,count=1)
nx=re.sub(r'codeName="[^"]*"','codeName="Fukunishi1030"',nx,count=1)
nx=re.sub(r'xr:uid="[^"]*"','xr:uid="{'+str(uuid.uuid4()).upper()+'}"',nx,count=1)
# 今回シートだけA4縦1ページへ。既存ページ設定には触れない。
nx=re.sub(r'<pageSetup\b[^>]*?/>',lambda m:re.sub(r'\s+(paperSize|orientation|fitToWidth|fitToHeight|scale)="[^"]*"','',m[0])[:-2]+' paperSize="9" orientation="portrait" fitToWidth="1" fitToHeight="1"/>',nx,count=1)
if '<pageSetUpPr' in nx:
 nx=re.sub(r'<pageSetUpPr\b[^>]*?/>',lambda m:re.sub(r'\s+fitToPage="[^"]*"','',m[0])[:-2]+' fitToPage="1"/>',nx,count=1)
else:nx=nx.replace('</sheetPr>','<pageSetUpPr fitToPage="1"/></sheetPr>',1)
sid=max(int(s.get('sheetId')) for s in sheets)+1
wxml=wxml.replace('<sheets>',f'<sheets><sheet name="{TAB}" sheetId="{sid}" r:id="{rid}"/>',1)
wxml=re.sub(r'localSheetId="(\d+)"',lambda m:f'localSheetId="{int(m[1])+1}"',wxml)
dn=f'<definedName name="_xlnm.Print_Area" localSheetId="0">\'{TAB}\'!$B$2:$H$44</definedName>'
if '<definedNames>' in wxml:wxml=wxml.replace('<definedNames>','<definedNames>'+dn,1)
else:wxml=wxml.replace('</sheets>','</sheets><definedNames>'+dn+'</definedNames>',1)
wxml=re.sub(r'<calcPr\b[^>]*/>','<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>',wxml,count=1)
wxml=re.sub(r'<workbookView\b[^>]*?/>',lambda m:re.sub(r'\s+activeTab="[^"]*"','',m[0])[:-2]+' activeTab="0"/>',wxml,count=1)
payload=old.copy();payload['xl/workbook.xml']=wxml.encode()
payload['xl/_rels/workbook.xml.rels']=rels.replace('</Relationships>',f'<Relationship Id="{rid}" Type="{REL}/worksheet" Target="worksheets/sheet{newnum}.xml"/></Relationships>').encode()
ct=old['[Content_Types].xml'].decode()
payload['[Content_Types].xml']=ct.replace('</Types>',f'<Override PartName="/{newpath}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>').encode()
payload[newpath]=nx.encode()
tr=posixpath.dirname(template)+'/_rels/'+posixpath.basename(template)+'.rels'
if tr in old:payload[f'xl/worksheets/_rels/sheet{newnum}.xml.rels']=old[tr]
for n in old:
 if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n):payload[n]=old[n].replace(b'tabSelected="1"',b'tabSelected="0"')
OUT.parent.mkdir(parents=True,exist_ok=True)
assert not (B/'verification.json').exists(),'保存完了済みデータは上書きしません'
with ZipFile(OUT,'w') as z:
 z.comment=comment
 for i in infos:z.writestr(i,payload[i.filename])
 for n in payload.keys()-old.keys():z.writestr(n,payload[n])
before=openpyxl.load_workbook(BACK,data_only=False);after=openpyxl.load_workbook(OUT,data_only=False)
assert after.sheetnames==[TAB]+before.sheetnames
s=after[TAB]
for addr,expected in edits.items():
 if addr=='G4':assert s[addr].value.date().isoformat()=='2026-10-30'
 else:assert s[addr].value==expected,(addr,s[addr].value,expected)
assert s['G17'].value=='=E17*F17' and s['G41'].value=='=SUM(G17:G40)'
assert s['C10'].value=='生産技術部' and s['C11'].value=='生産技術部 幸田宛'
assert '$B$2:$H$44' in str(s.print_area) and str(s.page_setup.paperSize)=='9'
for prev in before:
 cur=after[prev.title];assert str(prev.print_area)==str(cur.print_area)
 for row in prev:
  for c in row:
   v=cur[c.coordinate];assert c.value==v.value,(prev.title,c.coordinate)
   for a in ('font','fill','border','alignment','protection','number_format'):
    assert copy.copy(getattr(c,a))==copy.copy(getattr(v,a)),(prev.title,c.coordinate,a)
before.close();after.close()
cached=openpyxl.load_workbook(OUT,data_only=True)
assert cached[TAB]['G17'].value==cached[TAB]['G41'].value==10500
cached.close()
with ZipFile(OUT) as z:assert z.testzip() is None
assert not S.with_name('~$'+S.name).exists() and sha(S)==info['sha256']
shutil.copyfile(OUT,S);assert sha(S)==sha(OUT)
result={'source':str(S),'output':str(OUT),'backup':str(BACK),'sha256':sha(S),'tab':TAB,'order_no':'AF-K261030-1',
 'quote_no':'QT080-20261030-3','model':'AFPG804','quantity':10,'unit_price':1050,'total_ex_tax':10500,
 'billing':'生産技術部','delivery':'生産技術部 幸田宛','old_sheets_preserved':4,'printed':False}
(B/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
