from pathlib import Path,PurePosixPath
import json,sys,re
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-fix-20261105')
m=json.loads((b/'build.json').read_text(encoding='utf-8'));pub=json.loads((b/'published.json').read_text(encoding='utf-8'));stage=json.loads((b/'stage.json').read_text(encoding='utf-8'));snap=json.loads((b/'project.json').read_text(encoding='utf-8'))
p=sm.Project(pub['output']);inside=sm.Project(m['internal']);assert p.fingerprint==pub['sha256']==stage['candidate_sha256'];assert inside.fingerprint==m['internal_sha']
assert Path(pub['output']).read_bytes()==Path(stage['candidate']).read_bytes()
assert sm.sha(Path(pub['archived_source']).read_bytes())==m['external_sha']
before={s['key']:s for s in snap['sections']}
for s in p.sections:
    if s['name']!='Destacker_段バラシ':assert s['rows']==before[s['key']]['rows']
assert p.solution_names==[m['solution_name']]
# 宣言差分を、既存属性の変更なし＋Busy1個だけに限定。
olddecl=inside.declarations();newdecl=p.declarations();added=[]
for part,fields in olddecl.items():
    target=newdecl[part]
    originals={x['N']:x for x in fields};current={x['N']:x for x in target}
    assert all(current[n]==v for n,v in originals.items()),part
    added.extend((part,n,current[n]) for n in current.keys()-originals.keys())
assert len(added)==1 and added[0][1]=='Destacker_Init_Busy' and added[0][2]['R']=='0'
report={'output':pub['output'],'sha256':p.fingerprint,'project_name':p.solution_names[0],'internal_H_unchanged':True,'internal_H_sha256':inside.fingerprint,'previous_external_archived':pub['archived_source'],'user_updates_preserved':True,'existing_step_numbers_preserved':'Destacker_M[1]～[25]','added_step_elements':'[26]初回済み、[27]～[32]各移動の前完了解除確認','new_variable':added[0][2],'rows_before':21,'rows_after':29,'all_other_24_sections_identical':True,'existing_declarations_unchanged':True,'native':json.loads((b/'native.json').read_text(encoding='utf-8-sig')),'conditions':json.loads((b/'conditions.json').read_text(encoding='utf-8'))}
sm.save_json(out/'検証結果.json',report)
lines=['現在の行番号と処理（I版・0行目始まり）']
for i,r in enumerate(p.section('Destacker_段バラシ')['rows']):lines.append(str(i)+'行：'+r.get('CMT','').replace('\r\n',' / '))
(out/'I版の行番号一覧.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['native','conditions']},ensure_ascii=False))
