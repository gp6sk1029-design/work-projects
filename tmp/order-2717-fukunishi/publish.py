import hashlib,json,re,shutil,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
d=Path(__file__).parent
m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
before=d/'before.xlsx'; candidate=d/'candidate.xlsx'; target=Path(m['path'])
q='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ns={'s':q[1:-1]}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ss(z):
 if 'xl/sharedStrings.xml' not in z.namelist():return []
 return [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
def val(c,strings):
 if c.get('t')=='inlineStr':return ''.join(c.find(q+'is').itertext())
 v=c.find(q+'v')
 if v is None:return None
 return strings[int(v.text)] if c.get('t')=='s' else v.text
def cells(z,n):return {c.get('r'):c for c in ET.fromstring(z.read(n)).findall('.//s:c',ns)}
def patch_cell(xml,addr,body,newtype):
 pattern=r'<c\b[^>]*\br="'+addr+r'"[^>]*?(?:/>|>.*?</c>)'
 def replace(mt):
  tag=mt.group(0);head=tag[:tag.index('>')+1].replace('/>','>')
  head=re.sub(r'\s+t="[^"]*"','',head)
  if newtype:head=head[:-1]+' t="'+newtype+'">'
  return head+body+'</c>'
 xml,n=re.subn(pattern,replace,xml,count=1,flags=re.S)
 assert n==1,addr
 return xml

new_values={f'{col}{r}':v for r,row in enumerate(m['items'],16) for col,v in zip('BCDEF',row)}
book_before=openpyxl.load_workbook(before,read_only=True,data_only=False)
book_candidate=openpyxl.load_workbook(candidate,read_only=True,data_only=False)
cached=openpyxl.load_workbook(candidate,read_only=True,data_only=True)
assert cached['電気部品']['G41'].value==m['total']
assert cached['電気部品']['G42'].value==m['total']
assert cached['集計表']['C14'].value==m['total']
for r,item in enumerate(m['items'],16):
 assert [cached['電気部品'][f'{c}{r}'].value for c in 'BCDEF']==item
 assert cached['電気部品'][f'G{r}'].value==item[3]*item[4]
 for s in book_before:
  for row in s.iter_rows():
   for c in row:
    assert c.value!=item[0], '既存明細に同品番あり'

outdir=d.parents[1]/'outputs'/'order-2717-fukunishi-20261021'
outdir.mkdir(parents=True,exist_ok=True)
result=outdir/target.name
cache_updates=[]
with zipfile.ZipFile(before) as a,zipfile.ZipFile(candidate) as b,zipfile.ZipFile(result,'w') as z:
 sa,sb=ss(a),ss(b)
 for info in a.infolist():
  raw=a.read(info.filename)
  if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',info.filename):
   idx=int(re.search(r'sheet(\d+)',info.filename).group(1))-1
   s=book_before.worksheets[idx];cand=book_candidate[s.title]
   orig=cells(a,info.filename); newer=cells(b,info.filename)
   xml=raw.decode('utf-8')
   if s.title=='電気部品':
    for addr,value in new_values.items():
     c=newer[addr]
     assert str(val(c,sb))==str(value)
     body='<is><t>'+escape(value)+'</t></is>' if isinstance(value,str) else '<v>'+str(value)+'</v>'
     xml=patch_cell(xml,addr,body,'inlineStr' if isinstance(value,str) else None)
   # 数式は元のものを保持し、専用計算ツールで再計算できた変化分のみキャッシュを更新。
   for addr,c in orig.items():
    if c.find(q+'f') is None or addr not in newer:continue
    nc=newer[addr]
    old_value,new_value=val(c,sa),val(nc,sb)
    if old_value==new_value or new_value is None:continue
    if s[addr].value!=cand[addr].value:continue
    if nc.get('t')=='e':continue  # 関係のない既存計算の非対応結果を反映しない。
    fxml=ET.tostring(c.find(q+'f'),encoding='unicode')
    # 元の数式タグを再シリアライズせず、文字列のまま保持。
    match=re.search(r'<c\b[^>]*\br="'+addr+r'"[^>]*>.*?</c>',xml,re.S)
    assert match
    formula=re.search(r'<f\b[^>]*(?:/>|>.*?</f>)',match.group(0),re.S).group(0)
    newtype='str' if nc.get('t') in ('str','inlineStr','s') else nc.get('t')
    body=formula+'<v>'+escape(str(new_value))+'</v>'
    xml=patch_cell(xml,addr,body,newtype)
    cache_updates.append((s.title,addr))
   raw=xml.encode('utf-8')
  z.writestr(info,raw)

# 数式と全入力値・書式IDを照合。変更を許すのは30入力セルと数式キャッシュのみ。
final=openpyxl.load_workbook(result,read_only=True,data_only=False)
assert final.sheetnames==book_before.sheetnames
formulas=0
for old in book_before:
 new=final[old.title]
 new_cells={c.coordinate:c for row in new.iter_rows() for c in row if hasattr(c,'coordinate')}
 for row in old.iter_rows():
  for c in row:
   if not hasattr(c,'coordinate'):continue
   nc=new_cells[c.coordinate]
   expected=new_values.get(c.coordinate,c.value) if old.title=='電気部品' else c.value
   assert nc.value==expected,(old.title,c.coordinate,nc.value,expected)
   assert getattr(nc,'_style_id',0)==getattr(c,'_style_id',0)
   if c.data_type=='f':formulas+=1
final.close()
with zipfile.ZipFile(before) as a,zipfile.ZipFile(result) as z:
 assert a.namelist()==z.namelist() and z.testzip() is None
 for n in a.namelist():
  if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n):assert a.read(n)==z.read(n),n
v=openpyxl.load_workbook(result,read_only=True,data_only=True)
assert v['電気部品']['G41'].value==v['電気部品']['G42'].value==v['集計表']['C14'].value==1398000
v.close()
for wb in (book_before,book_candidate,cached):wb.close()
assert not list(target.parent.glob('~$*'))
assert sha(target)==m['sha256'],'編集開始後にファイルが変更されています'
shutil.copyfile(result,target)
assert sha(target)==sha(result)
report={'file':str(target),'sheet':'電気部品','range':'B16:F21','items':m['items'],
 'total_ex_tax':1398000,'formulas_preserved':formulas,'cache_updates':cache_updates,
 'sha256':sha(target),'date_delivery_unchanged':True,'backup':str(before)}
(d/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('items','cache_updates')},ensure_ascii=False,indent=2))
