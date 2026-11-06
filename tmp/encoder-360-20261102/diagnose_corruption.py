"""誤った出力と編集前のセル一覧をXMLとして比較する。"""
from pathlib import Path
import hashlib
import json
import zipfile
import xml.etree.ElementTree as E

base=Path(__file__).parent
paths={'backup':base/'編集前バックアップ.xlsx','bad_output':base.parent.parent/'outputs/encoder-360-20261102/1029_1332エンコーダ基準.xlsx','desktop':Path(r'C:\Users\SEIGI-N13\Desktop\1029_1332エンコーダ基準.xlsx'),'user_ver2':Path(r'C:\Users\SEIGI-N13\Desktop\新しいフォルダー\1029_1332エンコーダ基準_Ver2.xlsx')}
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
result={};cells={}
for label,p in paths.items():
    if not p.is_file():continue
    data=p.read_bytes()
    with zipfile.ZipFile(p) as z:
        root=E.fromstring(z.read('xl/worksheets/sheet8.xml'))
        cells[label]={c.get('r'):E.tostring(c,encoding='unicode') for c in root.findall('.//m:c',ns)}
        result[label]={'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'cells':len(cells[label]),'J14':cells[label].get('J14'),'G14':cells[label].get('G14'),'chain_bytes':len(z.read('xl/calcChain.xml')) if 'xl/calcChain.xml' in z.namelist() else 0}
for label in cells:
    if label=='backup':continue
    result[label]['missing_cells']=sorted(set(cells['backup'])-set(cells[label]))
    result[label]['missing_count']=len(result[label]['missing_cells'])
(base/'corruption_diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
