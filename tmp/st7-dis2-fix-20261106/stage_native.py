from pathlib import Path
from argparse import Namespace
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;meta=json.loads((b/'build.json').read_text(encoding='utf-8'))
r=sm.stage(Namespace(source=meta['base'],plan=str(b/'plan.json'),output=meta['stage'],report=str(b/'stage.json')))
try:
    n=sm.native(Namespace(source=meta['stage'],report=str(b/'native.json'),install_root='C:/Program Files (x86)/OMRON/Sysmac Studio'))
except Exception:
    n=json.loads((b/'native.json').read_text(encoding='utf-8-sig'));print(json.dumps({k:n[k] for k in ['rows','parse_fail','model_fail','missing_connections','errors']},ensure_ascii=False));raise
print(json.dumps({k:n[k] for k in ['rows','coils','parse_fail','model_fail','missing_connections','verified','sha256']},ensure_ascii=False))
