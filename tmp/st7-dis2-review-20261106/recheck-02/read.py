"""最新の登録Jと直前の確認対象を照合する。"""
from pathlib import Path
from xml.etree import ElementTree as E
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;b.mkdir(exist_ok=True)
old=json.loads((b.parent/'recheck-01/snapshot.json').read_text(encoding='utf-8'))
found=[x for x in sm.find_projects('C:/OMRON/Data/Solution','20261105J')['matches'] if x['name'].endswith('20261105J')];assert len(found)==1
p=sm.Project(found[0]['directory']);new={'path':str(p.path),'sha':p.fingerprint,'solution':found[0]['name'],'date':E.fromstring(p.entries[p.path.name+'.xml']).find('.//DateModified').text,'sections':p.sections,'variables':p.variable_parts}
sm.save_json(b/'snapshot.json',new)
a={s['name']:s['rows'] for s in old['sections']};diff=[]
for sec in p.sections:
    if sec['rows']!=a[sec['name']]:diff.append({'section':sec['name'],'changed_rows':[i for i,r in enumerate(sec['rows']) if i>=len(a[sec['name']]) or r!=a[sec['name']][i]],'old_count':len(a[sec['name']]),'new_count':len(sec['rows'])})
sm.save_json(b/'changes.json',diff)
print(json.dumps({'date':new['date'],'sha':new['sha'],'changes_since_last_review':diff,'source_unchanged':p.current_fingerprint()==p.fingerprint},ensure_ascii=False,indent=2))
