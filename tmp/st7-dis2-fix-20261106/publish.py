"""最終検査に一致した候補だけを、指定先A版へ保存する。"""
from pathlib import Path
from argparse import Namespace
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;out=Path('C:/Users/SEIGI-N13/work-projects/outputs/st7-dis2-fix-20261106');m=json.loads((b/'build.json').read_text(encoding='utf-8'));a=json.loads((b/'audit.json').read_text(encoding='utf-8'))
assert sm.Project(m['source_internal']).fingerprint==m['internal_sha'],'編集中にJが更新されたため公開せず再照合する'
assert sm.Project(m['stage']).fingerprint==a['sha256']
dest=Path(m['destination']).resolve();assert dest.parent==Path(m['base']).resolve().parent and dest.name.endswith('_20261106A.smc2')
r=sm.publish(Namespace(stage_report=str(b/'stage.json'),native_report=str(b/'native.json'),destination=str(dest),report=str(out/'保存結果.json'),history=None,overwrite=True,allow_logic=True,archive_source=False))
q=sm.Project(dest);assert q.fingerprint==a['sha256'];assert q.solution_names==[m['solution']]
assert sm.Project(m['source_internal']).fingerprint==m['internal_sha']
print(json.dumps(r,ensure_ascii=False,indent=2))
