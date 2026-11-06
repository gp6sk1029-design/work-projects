"""完成した原本へ書き込まず、コピーだけで処理完了時間を測る。"""
from pathlib import Path
import hashlib
import json
import subprocess
import time
import zipfile
import xml.etree.ElementTree as E

base=Path(__file__).resolve().parent
source=Path(r'C:\Users\SEIGI-N13\Desktop\【業務報告2026 Ver2.7】幸田.xlsx')
node=Path(r'C:\Users\SEIGI-N13\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe')
digest=lambda b:hashlib.sha256(b).hexdigest()
t=time.perf_counter()
data=source.read_bytes()
source_hash=digest(data)
(base/'freeze-source.xlsx').write_bytes(data)
with zipfile.ZipFile(base/'freeze-source.xlsx') as z:
    assert z.testzip() is None
    count=len(z.namelist())
read_seconds=time.perf_counter()-t
t=time.perf_counter()
completed=subprocess.run([str(node),str(base/'edit.mjs'),'probe'],capture_output=True,text=True,encoding='utf-8',timeout=60)
elapsed=time.perf_counter()-t
(base/'freeze-test-process.log').write_text(completed.stdout+'\n'+completed.stderr,encoding='utf-8')
assert completed.returncode==0,completed.stderr[-2000:]
dest=base/'freeze-test-only.xlsx'
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    w=E.fromstring(z.read('xl/workbook.xml'))
    s=next(x for x in w.find('m:sheets',ns) if x.get('name')=='10月')
    rid=s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
    target=next(x.get('Target') for x in E.fromstring(z.read('xl/_rels/workbook.xml.rels')) if x.get('Id')==rid)
    path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
    root=E.fromstring(z.read(path))
    cell=next(x for x in root.findall('.//m:c',ns) if x.get('r')=='BS100')
    assert float(cell.find('m:v',ns).text)==123.456
after_hash=digest(source.read_bytes())
result={'source_sha256_before':source_hash,'source_sha256_after':after_hash,'source_unchanged_during_test':source_hash==after_hash,'source_write_operations':0,'zip_entries':count,'copy_and_zip_read_seconds':round(read_seconds,3),'import_edit_export_seconds':round(elapsed,3),'timeout_seconds':60,'saved_test_value_verified':True,'process_exit_code':completed.returncode,'native_excel_test':False,'attachment_send_test':False,'test_file_is_disposable':True,'stdout':completed.stdout.strip()}
(base/'freeze-test-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
