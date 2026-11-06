"""更新された登録Jを前回の保存スナップショットと照合。"""
from pathlib import Path
from xml.etree import ElementTree as E
import sys,json,difflib
sys.path.insert(0,'C:/Users/SEIGI-N13/work-projects/.agents/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;b.mkdir(exist_ok=True);old=json.loads((b.parent/'snapshot.json').read_text(encoding='utf-8'))
found=[x for x in sm.find_projects('C:/OMRON/Data/Solution','20261105J')['matches'] if x['name'].endswith('20261105J')];assert len(found)==1
p=sm.Project(found[0]['directory']);new={'path':str(p.path),'sha':p.fingerprint,'solution':found[0]['name'],'date':E.fromstring(p.entries[p.path.name+'.xml']).find('.//DateModified').text,'sections':p.sections,'variables':p.variable_parts}
sm.save_json(b/'snapshot.json',new)
os={x['name']:x for x in old['sections']};diff=[]
for sec in p.sections:
    prior=os[sec['name']];a=[sm.jsha(sm.without_comment(r)) for r in prior['rows']];z=[sm.jsha(sm.without_comment(r)) for r in sec['rows']]
    changes=[]
    if a==z:continue
    for op,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes():
        if op!='equal':changes.append({'op':op,'old_rows':list(range(i,j)),'new_rows':list(range(k,l))})
    diff.append({'section':sec['name'],'old_count':len(a),'new_count':len(z),'changes':changes})
sm.save_json(b/'changes.json',diff)
print(json.dumps({'date':new['date'],'old_sha':old['sha'],'new_sha':new['sha'],'changes':diff},ensure_ascii=False,indent=2))
names={'ST7_A_Dis2_左SF排出','Output_出力','RCON_IAI'}
for item in diff:
    if item['section'] not in names:continue
    sec=p.section(item['section'])
    for ch in item['changes']:
        for i in ch['new_rows']:
            r=sec['rows'][i];print('\n',sec['name'],'ROW',i,r.get('CMT','').replace('\r\n',' / '))
            cs=[]
            for c in r['CLs']:
                if c['__type']=='HL':continue
                a={k:c[k] for k in ['__type','Var','Name','Not','S','RS','X','Y','TXT'] if k in c}
                for io in ['In','Out']:
                    if io in c:a[io]=[(v.get('Arg'),v.get('Var')) for v in c[io] if v.get('Var')]
                cs.append(a)
            print(json.dumps({'cells':cs,'VLs':r['VLs']},ensure_ascii=False))
