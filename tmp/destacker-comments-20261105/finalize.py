from pathlib import Path,PurePosixPath
from zipfile import ZipFile
import sys,json,re
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-comments-20261105')
original=json.loads((out/'直接反映結果.json').read_text(encoding='utf-8'));names=json.loads((out/'変数コメント直接反映結果.json').read_text(encoding='utf-8'))
before=sm.Project(original['backup']);after=sm.Project(original['project']);reference=sm.Project(b/'I_all_comments.smc2')
assert set(before.entries)==set(after.entries)
parts=[x for x in before.entries if before.entries[x]!=after.entries[x]]
expected={c['part'] for c in original['changed']}|{c['part'] for c in names['changed']}
assert set(parts)==expected and len(parts)==4
assert not sm.comparison(before,after)['control_difference']
assert before.declarations()==after.declarations()==reference.declarations()
for a,c in sm.align(after,reference):assert a['rows']==c['rows']
rows=after.section('Destacker_段バラシ')['rows'];old=before.section('Destacker_段バラシ')['rows']
assert len(rows)==len(old)==29
assert all(sm.without_comment(a)==sm.without_comment(c) for a,c in zip(rows,old))
assert all(a.get('CMT')!=c.get('CMT') for a,c in zip(rows,old))
def only_declarations(raw):return '\n'.join(re.sub(r'\t(?:Com|EC)=[^\t\r\n]*','',line) for line in raw.decode('utf-8-sig').splitlines())
for c in names['changed']:assert only_declarations(before.entries[c['part']])==only_declarations(after.entries[c['part']])
stage=json.loads((b/'name-native.json').read_text(encoding='utf-8-sig'))
assert stage['verified'] and stage['sha256']==reference.fingerprint
report={'project':original['solution'],'internal_directory':original['project'],'before_sha':original['project_sha256_before'],'after_sha':after.fingerprint,'backup':original['backup'],'backup_files':len(before.entries),'changed_files':parts,'unchanged_files':len(before.entries)-len(parts),'row_comments_updated':29,'step_element_comments_updated':32,'logic_identical':True,'variable_declarations_identical':True,'only_CMT_Com_EC_changed':True,'native':{'rows':stage['rows'],'parse_fail':stage['parse_fail'],'model_fail':stage['model_fail'],'missing_connections':stage['missing_connections']},'user_confirmed_closed':True,'ui_reflection_verified':False,'external_desktop_smc2_updated':False}
sm.save_json(out/'最終検証結果.json',report);print(json.dumps(report,ensure_ascii=False))
