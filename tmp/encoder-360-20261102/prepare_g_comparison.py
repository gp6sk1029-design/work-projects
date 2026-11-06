"""最新の比較ブックを退避してG4:G363の保存値を確認する。"""
from pathlib import Path
from lxml import etree as E
import json, zipfile, hashlib, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
p=Path(r'C:\Users\SEIGI-N13\Desktop\1029_1332エンコーダ基準_比較グラフ.xlsx')
backup=b/'G列変更前バックアップ.xlsx'
if not backup.exists(): shutil.copy2(p,backup)
assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(backup.read_bytes()).digest()
n={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(backup) as z:
 root=E.fromstring(z.read('xl/worksheets/sheet8.xml'))
 cells={c.get('r'):c for c in root.xpath('//m:c',namespaces=n)}
 values=[]
 for row in range(4,364):
  cell=cells['G'+str(row)]
  v=cell.findtext('m:v',namespaces=n)
  assert v is not None and cell.get('t') not in ['e','s','str']
  values.append({'row':row,'value':v,'formula':cell.findtext('m:f',namespaces=n)})
 info={'source':str(backup),'desktop':str(p),'sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'G':values}
 (b/'comparison_inspection.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'count':len(values),'first':values[0],'last':values[-1],'sha256':info['sha256']},ensure_ascii=False))
