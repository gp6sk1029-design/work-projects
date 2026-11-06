from pathlib import Path
import sys,json,shutil
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
from PIL import Image
b=Path(__file__).parent;out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-recheck-20261105')
d=json.loads((b/'project.json').read_text(encoding='utf-8'));inside=sm.Project(d['internal']);outside=sm.Project(d['external'])
v={'internal_before':d['internal_sha256'],'internal_after':inside.fingerprint,'internal_unchanged':d['internal_sha256']==inside.fingerprint,'external_before':d['external_sha256'],'external_after':outside.fingerprint,'external_unchanged':d['external_sha256']==outside.fingerprint,'comparison':sm.comparison(inside,outside),'images':{p.name:list(Image.open(p).size) for p in out.glob('*.png')}}
(out/'読取り不変確認.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(b/'checks.json',out/'条件確認.json')
print(json.dumps(v,ensure_ascii=False))
