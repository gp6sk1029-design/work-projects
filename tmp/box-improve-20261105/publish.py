"""検証済みE版を保存後、元D版を履歴へ移動する。"""
from pathlib import Path
import json,hashlib,os
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
assert m['native_validation'] and m['independent_audit']
assert 'MISSING=0 PARSE_MODEL_FAIL=0' in m['native_validation']['connections']
assert m['independent_audit']['handshake_model_scenarios']==24 and m['independent_audit']['output_OR_equivalence_cases']==1024
src=Path(m['source']);dest=Path(m['output']);archive=Path(m['archive']);stage=Path(m['staged'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
data=stage.read_bytes();assert hashlib.sha256(data).hexdigest()==m['output_sha256']
assert not dest.exists() and not archive.exists()
root=src.parent.resolve();assert src.resolve().parent==root and dest.resolve().parent==root
assert archive.parent.resolve().is_relative_to(root)
with dest.open('xb') as f:f.write(data)
assert dest.read_bytes()==data
archive.parent.mkdir(exist_ok=True)
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
os.rename(src,archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['source_sha256']
m['published']=True;m['archived']=True
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(dest),'archive':str(archive),'sha256':m['output_sha256'],'native':m['native_validation']},ensure_ascii=False))
