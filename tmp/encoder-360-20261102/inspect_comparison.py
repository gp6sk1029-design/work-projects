from pathlib import Path
from lxml import etree as E
import zipfile, json, hashlib, sys
sys.stdout.reconfigure(encoding='utf-8')
p=Path(r'C:\Users\SEIGI-N13\Desktop\1029_1332エンコーダ基準_修正版.xlsx')
n={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart','a':'http://schemas.openxmlformats.org/drawingml/2006/main','m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(p) as z:
 charts=[]
 for name in z.namelist():
  if name.startswith('xl/charts/chart') and name.endswith('.xml'):
   r=E.fromstring(z.read(name)); charts.append({'part':name,'title':r.xpath('//c:title//a:t/text()',namespaces=n),'series': [{'formulas':s.xpath('.//c:f/text()',namespaces=n),'count':s.xpath('.//c:ptCount/@val',namespaces=n)} for s in r.xpath('//c:ser',namespaces=n)]})
 r=E.fromstring(z.read('xl/worksheets/sheet8.xml'))
 cells={c.get('r'):c for c in r.xpath('//m:c',namespaces=n)}
 values=[]
 for row in range(4,364):
  c=cells.get('J'+str(row)); values.append({'row':row,'value':c.findtext('m:v',namespaces=n) if c is not None else None,'formula':c.findtext('m:f',namespaces=n) if c is not None else None})
 data={'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'charts':charts,'J':values}
 for name in ['xl/drawings/_rels/drawing5.xml.rels','xl/worksheets/_rels/sheet8.xml.rels']:
  if name in z.namelist(): print(name, z.read(name).decode())
 for name in ['xl/charts/chart5.xml','xl/charts/chart4.xml']:
  r=E.fromstring(z.read(name))
  print(name, 'type',r.xpath('local-name(//c:ser/..)',namespaces=n),'series',E.tostring(r.find('.//c:ser',n),encoding='unicode')[:1800])
 (Path(__file__).parent/'comparison_inspection.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'sha256':data['sha256'],'charts':charts,'J_count':len(values),'J_blanks':[v['row'] for v in values if v['value'] is None],'J_first':values[:3],'J_last':values[-3:]},ensure_ascii=False))
