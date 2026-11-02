import hashlib,json,re,shutil,sys,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape
import openpyxl
from openpyxl.utils.datetime import to_excel
sys.stdout.reconfigure(encoding='utf-8')
d=Path(__file__).parent;m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
src=d/'before.xlsx';candidate=d/'candidate.xlsx';target=Path(m['path'])
q='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}';ns={'s':q[1:-1]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def strings(z):
 return [''.join(c.itertext()) for c in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
def val(c,ss):
 if c.get('t')=='inlineStr':return ''.join(c.find(q+'is').itertext())
 v=c.find(q+'v')
 return None if v is None else ss[int(v.text)] if c.get('t')=='s' else v.text
def patch(xml,addr,body,typ):
 def sub(mt):
  text=mt.group(0);head=text[:text.index('>')+1].replace('/>','>')
  head=re.sub(r'\s+t="[^"]*"','',head)
  if typ:head=head[:-1]+' t="'+typ+'">'
  return head+body+'</c>'
 xml,n=re.subn(r'<c\b[^>]*\br="'+addr+r'"[^>]*?(?:/>|>.*?</c>)',sub,xml,count=1,flags=re.S)
 assert n==1,addr
 return xml
a_w=openpyxl.load_workbook(src,read_only=True,data_only=False)
b_w=openpyxl.load_workbook(candidate,read_only=True,data_only=False)
b_v=openpyxl.load_workbook(candidate,read_only=True,data_only=True)
assert b_v['巻線']['G41'].value==b_v['巻線']['G42'].value==b_v['集計表']['C19'].value==712000
assert b_v['電気部品']['G41'].value==1398000
out=d.parents[1]/'outputs'/'order-2717-techno-20261021';out.mkdir(parents=True,exist_ok=True)
result=out/target.name;updated={};changed=[]
with zipfile.ZipFile(src) as a,zipfile.ZipFile(candidate) as b,zipfile.ZipFile(result,'w') as z:
 sa,sb=strings(a),strings(b)
 for info in a.infolist():
  raw=a.read(info.filename)
  if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',info.filename):
   idx=int(re.search(r'sheet(\d+)',info.filename).group(1))-1
   s=a_w.worksheets[idx];xml=raw.decode('utf-8')
   orig={c.get('r'):c for c in ET.fromstring(raw).findall('.//s:c',ns)}
   newer={c.get('r'):c for c in ET.fromstring(b.read(info.filename)).findall('.//s:c',ns)}
   allowed=set()
   if s.title=='巻線':
    for addr,value in m['updates'].items():
     cv=val(newer[addr],sb)
     assert (str(cv)==value if isinstance(value,str) else float(cv)==value),addr
     typ='inlineStr' if isinstance(value,str) else None
     body='<is><t>'+escape(value)+'</t></is>' if typ else '<v>'+str(value)+'</v>'
     xml=patch(xml,addr,body,typ);allowed.add(addr)
   # 変更対象ページと集計表の計算キャッシュのみ更新。他の業者ページには触れない。
   if s.title in ('巻線','集計表'):
    for addr,c in orig.items():
     if c.find(q+'f') is None or addr not in newer:continue
     if s.title=='巻線' and addr not in ['G16','G17','G41','G42']:continue
     nc=newer[addr];nv=val(nc,sb)
     if nv is None or nc.get('t')=='e' or val(c,sa)==nv:continue
     if a_w[s.title][addr].value!=b_w[s.title][addr].value:continue
     match=re.search(r'<c\b[^>]*\br="'+addr+r'"[^>]*>.*?</c>',xml,re.S)
     f=re.search(r'<f\b[^>]*?(?:/>|>.*?</f>)',match.group(0),re.S).group(0)
     typ='str' if nc.get('t') in ('s','str','inlineStr') else nc.get('t')
     xml=patch(xml,addr,f+'<v>'+escape(str(nv))+'</v>',typ);allowed.add(addr)
   raw=xml.encode('utf-8')
   if raw!=a.read(info.filename):
    changed.append(info.filename);updated[s.title]=sorted(allowed)
   # 許可セル以外のXML構造（入力規則・表示・印刷設定等）が全て同一であること。
   x=ET.fromstring(a.read(info.filename));y=ET.fromstring(raw)
   for root in (x,y):
    for c in root.findall('.//s:c',ns):
     if c.get('r') in allowed:c.clear()
   assert ET.tostring(x)==ET.tostring(y),s.title
  z.writestr(info,raw)
with zipfile.ZipFile(src) as a,zipfile.ZipFile(result) as z:
 assert a.namelist()==z.namelist() and z.testzip() is None
 for n in a.namelist():
  if n not in changed:assert a.read(n)==z.read(n)
final=openpyxl.load_workbook(result,read_only=True,data_only=False)
assert final.sheetnames==a_w.sheetnames
for old in a_w:
 mapped={c.coordinate:c for row in final[old.title].iter_rows() for c in row if hasattr(c,'coordinate')}
 for row in old.iter_rows():
  for c in row:
   if not hasattr(c,'coordinate'):continue
   nc=mapped[c.coordinate];expected=m['updates'].get(c.coordinate,c.value) if old.title=='巻線' else c.value
   actual=to_excel(nc.value) if isinstance(nc.value,datetime) and isinstance(expected,(int,float)) else nc.value
   assert actual==expected,(old.title,c.coordinate,actual,expected)
   assert getattr(c,'_style_id',0)==getattr(nc,'_style_id',0)
assert final['巻線']['C16'].alignment.shrinkToFit is True
final.close()
for w in (a_w,b_w,b_v):w.close()
assert not list(target.parent.glob('~$*')),'Excelが開かれています'
assert sha(target)==m['sha256'],'編集開始後に他者が更新しています'
shutil.copyfile(result,target);assert sha(target)==sha(result)
w=openpyxl.load_workbook(target,read_only=True,data_only=True)
assert w['巻線']['B4'].value=='株式会社テクノ'
assert w['巻線']['G3'].value==datetime(2026,10,21)
assert w['巻線']['C11'].value=='生産技術部 幸田宛て'
assert w['巻線']['G41'].value==w['巻線']['G42'].value==w['集計表']['C19'].value==712000
assert w['電気部品']['G41'].value==1398000
report={'path':str(target),'sha256':sha(target),'total_ex_tax':712000,'updates':m['updates'],
 'changed_xml':changed,'allowed_cells':updated,'other_pages_preserved':True,'dropdown_preserved':True}
(d/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('NAS保存・読戻し検証完了：テクノ712000円、福西1398000円を保持。',sha(target));w.close()
