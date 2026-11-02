import copy,hashlib,json,re,shutil,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
d=Path(__file__).parent;m=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
src=d/'before.xlsx';target=Path(m['path'])
q='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}';ns={'s':q[1:-1]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
w=openpyxl.load_workbook(src,read_only=True,data_only=False)
out=d.parents[1]/'outputs'/'order-2717-fit-equipment-20261021';out.mkdir(parents=True,exist_ok=True)
result=out/target.name
with zipfile.ZipFile(src) as a:
 styles=a.read('xl/styles.xml');root=ET.fromstring(styles);xfs=root.find(q+'cellXfs')
 old_count=len(xfs);mapping={};new_xfs=[]
 for sn,addresses in m['targets'].items():
  for addr in addresses:
   sid=w[sn][addr]._style_id
   if sid in mapping:continue
   if w[sn][addr].alignment.shrinkToFit is True:
    mapping[sid]=sid;continue
   xf=copy.deepcopy(xfs[sid]);al=xf.find(q+'alignment')
   if al is None:al=ET.SubElement(xf,q+'alignment')
   al.set('shrinkToFit','1');xf.set('applyAlignment','1')
   mapping[sid]=old_count+len(new_xfs);new_xfs.append(xf)
 def native_xml(node):
  return ET.tostring(node,encoding='unicode').replace('ns0:','').replace(' xmlns:ns0="'+q[1:-1]+'"','')
 sx=styles.decode('utf-8')
 sx=re.sub(r'(<cellXfs\b[^>]*\bcount=")[^"]*(")',lambda x:x.group(1)+str(old_count+len(new_xfs))+x.group(2),sx,count=1)
 sx=sx.replace('</cellXfs>',''.join(native_xml(x) for x in new_xfs)+'</cellXfs>')
 after_styles=ET.fromstring(sx);after_xfs=after_styles.find(q+'cellXfs')
 assert len(after_xfs)==old_count+len(new_xfs)
 for i in range(old_count):assert ET.tostring(xfs[i])==ET.tostring(after_xfs[i])
 # 元の全スタイルを維持し、追加スタイルは縮小表示と適用フラグ以外同じ。
 for old_sid,new_sid in mapping.items():
  if old_sid==new_sid:continue
  expected=copy.deepcopy(xfs[old_sid]);al=expected.find(q+'alignment')
  if al is None:al=ET.SubElement(expected,q+'alignment')
  al.set('shrinkToFit','1');expected.set('applyAlignment','1')
  assert ET.tostring(expected)==ET.tostring(after_xfs[new_sid])
 changed=[];count=0
 with zipfile.ZipFile(result,'w') as z:
  for info in a.infolist():
   raw=a.read(info.filename)
   if info.filename=='xl/styles.xml':raw=sx.encode('utf-8')
   elif re.fullmatch(r'xl/worksheets/sheet\d+\.xml',info.filename):
    idx=int(re.search(r'sheet(\d+)',info.filename).group(1))-1;sn=w.worksheets[idx].title
    if sn in m['targets']:
     xml=raw.decode('utf-8')
     for addr in m['targets'][sn]:
      old_sid=w[sn][addr]._style_id;new_sid=mapping[old_sid]
      if new_sid==old_sid:continue
      def sub(mt):
       head=mt.group(0)
       if re.search(r'\bs="\d+"',head):return re.sub(r'\bs="\d+"','s="'+str(new_sid)+'"',head,count=1)
       return head[:-1]+' s="'+str(new_sid)+'">'
      xml,n=re.subn(r'<c\b[^>]*\br="'+addr+r'"[^>]*>',sub,xml,count=1)
      assert n==1,(sn,addr);count+=1
     raw=xml.encode('utf-8')
     x=ET.fromstring(a.read(info.filename));y=ET.fromstring(raw)
     for node in (x,y):
      for c in node.findall('.//s:c',ns):
       if c.get('r') in m['targets'][sn]:c.attrib.pop('s',None)
     assert ET.tostring(x)==ET.tostring(y),sn
   if raw!=a.read(info.filename):changed.append(info.filename)
   z.writestr(info,raw)
w.close()
final=openpyxl.load_workbook(result,read_only=True,data_only=False)
for sn,addresses in m['targets'].items():
 for addr in addresses:assert final[sn][addr].alignment.shrinkToFit is True,(sn,addr)
final.close()
with zipfile.ZipFile(src) as a,zipfile.ZipFile(result) as b:
 assert a.namelist()==b.namelist() and b.testzip() is None
 for n in a.namelist():
  if n not in changed:assert a.read(n)==b.read(n)
assert not list(target.parent.glob('~$*')),'Excelが開かれています'
assert sha(target)==m['sha256'],'他者が更新しています。上書き中止'
shutil.copyfile(result,target);assert sha(target)==sha(result)
v=openpyxl.load_workbook(target,read_only=True,data_only=False)
assert all(v[sn][addr].alignment.shrinkToFit is True for sn,addresses in m['targets'].items() for addr in addresses)
v.close()
report={'path':str(target),'count':count,'sheets':len(m['targets']),'new_styles':len(new_xfs),'changed':changed,'sha256':sha(target),
 'content_formulas_merges_widths_unchanged':True,'excel_visual_check':'Excel実アプリの表示確認は未実施。縮小表示属性を全対象セルで読戻し検証。'}
(d/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
