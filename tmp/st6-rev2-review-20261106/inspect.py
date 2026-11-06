"""最新登録版の特定と読取り専用スナップショット。"""
from pathlib import Path
from xml.etree import ElementTree as E
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/work-projects/.agents/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;b.mkdir(exist_ok=True)
matches=sm.find_projects('C:/OMRON/Data/Solution','20261105')['matches'];summaries=[]
for m in matches:
    if not (m['name'].endswith('I') or m['name'].endswith('J') or m['name'].endswith('I_4')):continue
    p=sm.Project(m['directory']);sec=p.section('ST6_A_Rev2_左反転2')
    root=E.fromstring(p.entries[p.path.name+'.xml'])
    summaries.append({'name':m['name'],'path':str(p.path),'sha':p.fingerprint,'date':root.find('.//DateModified').text,'section_sha':sm.jsha(sec['rows']),'part':sec['part'],'rows':len(sec['rows'])})
    sm.save_json(b/(m['name'].split('_')[-1]+'-snapshot.json'),{'path':str(p.path),'sha':p.fingerprint,'sections':p.sections,'variables':p.variable_parts})
sm.save_json(b/'projects.json',summaries)
print(json.dumps(summaries,ensure_ascii=False,indent=2))
