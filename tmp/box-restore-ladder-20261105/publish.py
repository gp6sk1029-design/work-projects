from pathlib import Path
import json,hashlib,os
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
assert m['independent_audit']['new_ST_removed'] and m['native_validation']
assert 'MISSING=0 PARSE_MODEL_FAIL=0' in m['native_validation']['connections']
src=Path(m['source']);dest=Path(m['output']);stage=Path(m['staged']);archive=Path(m['archive'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
assert hashlib.sha256(Path(m['baseline']).read_bytes()).hexdigest()==m['baseline_sha256']
data=stage.read_bytes();assert hashlib.sha256(data).hexdigest()==m['output_sha256']
assert not dest.exists() and not archive.exists()
root=src.parent.resolve();assert dest.resolve().parent==root and archive.parent.resolve().is_relative_to(root)
with dest.open('xb') as f:f.write(data)
assert dest.read_bytes()==data
archive.parent.mkdir(exist_ok=True)
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
os.rename(src,archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['source_sha256']
m['published']=True;m['archived']=True
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(dest),'archive':str(archive),'hash':m['output_sha256']},ensure_ascii=False))
