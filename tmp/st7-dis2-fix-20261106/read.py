"""最新Jの全保存データを保全し、既存SMC2との差と今回ユーザー編集を確認。"""
from pathlib import Path,PurePosixPath
from xml.etree import ElementTree as E
from zipfile import ZipFile,ZIP_DEFLATED
import sys,json,re,difflib
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;b.mkdir(exist_ok=True);out=Path('C:/Users/SEIGI-N13/work-projects/outputs/st7-dis2-fix-20261106');out.mkdir(exist_ok=True)
old=json.loads(Path('C:/Users/SEIGI-N13/work-projects/tmp/st7-dis2-review-20261106/recheck-02/snapshot.json').read_text(encoding='utf-8'))
found=[x for x in sm.find_projects('C:/OMRON/Data/Solution','20261105J')['matches'] if x['name'].endswith('20261105J')];assert len(found)==1
p=sm.Project(found[0]['directory']);source=sm.Project('C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/0.DLデータ/OMRON/Codex編集用/3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105I.smc2')
backup=out/('J_編集前保存データ_'+sm.stamp()+'.zip')
with ZipFile(backup,'x',compression=ZIP_DEFLATED) as z:
    for k,v in p.entries.items():z.writestr(k,v)
with ZipFile(backup) as z:assert z.testzip() is None and all(z.read(k)==v for k,v in p.entries.items())
assert p.current_fingerprint()==p.fingerprint
new={'path':str(p.path),'sha':p.fingerprint,'solution':found[0]['name'],'date':E.fromstring(p.entries[p.path.name+'.xml']).find('.//DateModified').text,'sections':p.sections,'variables':p.variable_parts,'backup':str(backup),'base':str(source.path),'base_sha':source.fingerprint}
sm.save_json(b/'snapshot.json',new)
a={s['name']:s['rows'] for s in old['sections']};diff=[]
for sec in p.sections:
    if sec['rows']!=a[sec['name']]:diff.append({'section':sec['name'],'changed_rows':[i for i,r in enumerate(sec['rows']) if i>=len(a[sec['name']]) or r!=a[sec['name']][i]],'old_count':len(a[sec['name']]),'new_count':len(sec['rows'])})
sm.save_json(b/'changes.json',diff)
print(json.dumps({'date':new['date'],'sha':p.fingerprint,'changes_since_review':diff,'base_comparison':sm.comparison(source,p),'backup':str(backup)},ensure_ascii=False,indent=2))
sec=p.section('ST7_A_Dis2_左SF排出')
for n,r in enumerate(sec['rows']):
    print('ROW',n,r.get('CMT','').replace('\r\n',' / '))
    cs=[]
    for c in r['CLs']:
        if c['__type']=='HL':continue
        a={k:c[k] for k in ['__type','Var','Name','Not','S','RS','X','Y','TXT'] if k in c}
        for io in ['In','Out']:
            if io in c:a[io]=[(z.get('Arg'),z.get('Var')) for z in c[io] if z.get('Var')]
        cs.append(a)
    print(json.dumps({'cells':cs,'VLs':r['VLs']},ensure_ascii=False))
