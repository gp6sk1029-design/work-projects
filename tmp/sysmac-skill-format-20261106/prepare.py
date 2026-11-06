"""スキル３配置の差分確認と変更前保全。"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib,json
b=Path('C:/Users/SEIGI-N13/work-projects');out=b/'outputs/sysmac-skill-format-20261106';out.mkdir(parents=True,exist_ok=True)
roots=[b/'.claude/skills/sysmac-studio',b/'.agents/skills/sysmac-studio',Path('C:/Users/SEIGI-N13/.codex/skills/sysmac-studio')]
def files(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.pyo']}
source=files(roots[0]);states=[]
for root in roots:
    cur=files(root);delta=[k for k in set(source)|set(cur) if cur.get(k)!=source.get(k)];assert not delta,(str(root),delta)
    states.append({'root':str(root),'files':{k:hashlib.sha256(v).hexdigest() for k,v in cur.items()}})
backup=out/'変更前スキル.zip'
with ZipFile(backup,'x',compression=ZIP_DEFLATED) as z:
    for k,v in source.items():z.writestr(k,v)
with ZipFile(backup) as z:assert z.testzip() is None and all(z.read(k)==v for k,v in source.items())
(out/'変更前照合.json').write_text(json.dumps(states,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'backup':str(backup),'files':len(source),'all_three_equal':True},ensure_ascii=False))
