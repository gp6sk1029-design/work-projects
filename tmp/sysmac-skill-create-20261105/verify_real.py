"""実Hは読取りのみ。スキルの共通処理を実データへ適用する。"""
from pathlib import Path
from argparse import Namespace
import sys,json,time
scripts=Path('C:/Users/SEIGI-N13/work-projects/.claude/skills/sysmac-studio/scripts')
sys.path.insert(0,str(scripts))
import sysmac as sm
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/sysmac-skill-create-20261105');out.mkdir(parents=True,exist_ok=True)
meta=json.loads(Path('tmp/box-io-comment-20261105/verification.json').read_text(encoding='utf-8'))
internal_meta=json.loads(Path('tmp/sysmac-direct-save-20261105/verification.json').read_text(encoding='utf-8'))
external=Path(meta['output']);start=time.perf_counter();p=sm.Project(external);seconds=time.perf_counter()-start
internal=Path(internal_meta['internal_directory']);start=time.perf_counter();q=sm.Project(internal);diff=sm.comparison(p,q);compare_seconds=time.perf_counter()-start
check_before=p.fingerprint;internal_before=q.fingerprint
start=time.perf_counter();native=sm.native(Namespace(source=str(external),report=str(out/'実H_native読込み.json'),install_root='C:/Program Files (x86)/OMRON/Sysmac Studio'));native_seconds=time.perf_counter()-start
sm.check(native['verified'],'実Hの同梱読込み失敗')
sm.check(sm.sha(external.read_bytes())==check_before and q.current_fingerprint()==internal_before,'実データが検証中に変わりました')
result={'read_only':True,'external_sha256':check_before,'sections':len(p.sections),'rows':sum(len(s['rows']) for s in p.sections),
    'variable_tables':len(p.variable_parts),'inspect_seconds':round(seconds,4),'internal_compare_seconds':round(compare_seconds,4),'native_seconds':round(native_seconds,4),
    'internal_comparison':diff,'native':{k:native[k] for k in ['rows','coils','parse_fail','model_fail','missing_connections','verified']},'real_projects_unchanged':True}
sm.save_json(out/'実H_読取り検証.json',result);sm.emit(result)
