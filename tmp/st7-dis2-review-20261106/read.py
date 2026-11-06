"""ST7左SF排出を読取り、対象版と要求先を保存する。"""
from pathlib import Path
from xml.etree import ElementTree as E
import sys,json,re
sys.path.insert(0,'C:/Users/SEIGI-N13/work-projects/.agents/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;b.mkdir(exist_ok=True)
found=sm.find_projects('C:/OMRON/Data/Solution','2026110')['matches'];items=[]
for m in found:
    if not re.search(r'2026110[56][I-Z]$',m['name']):continue
    p=sm.Project(m['directory']);root=E.fromstring(p.entries[p.path.name+'.xml'])
    items.append((root.find('.//DateModified').text,p,m))
items.sort(key=lambda x:x[0],reverse=True);date,p,m=items[0]
sec=p.section('ST7_A_Dis2_左SF排出')
comparison=[]
for d,q,n in items:comparison.append({'name':n['name'],'path':str(q.path),'date':d,'sha':q.fingerprint,'section_sha':sm.jsha(q.section(sec['name'])['rows'])})
sm.save_json(b/'snapshot.json',{'path':str(p.path),'sha':p.fingerprint,'solution':m['name'],'date':date,'versions':comparison,'sections':p.sections,'variables':p.variable_parts})
def compact(r):
    cells=[]
    for c in r['CLs']:
        if c['__type']=='HL':continue
        a={k:c[k] for k in ['__type','Var','Name','Not','X','Y','TXT','STType'] if k in c}
        for pin in ['In','Out']:
            if c.get(pin):a[pin]=[{k:x[k] for k in ['Arg','Var','__type'] if k in x} for x in c[pin]]
        cells.append(a)
    return {'cells':cells,'VLs':r['VLs']}
lines=[]
for i,r in enumerate(sec['rows']):lines.extend([f'行 {i} '+r.get('CMT','').replace('\r\n',' / '),json.dumps(compact(r),ensure_ascii=False)])
(b/'target.txt').write_text('\n'.join(lines),encoding='utf-8')
tags=set(c['Var'].split('[')[0] for r in sec['rows'] for c in r['CLs'] if c['__type']=='ST')
tags.update(['A_SF_CT','HMI_A_SF_StackPitch_mm','ST7_A_Dis2_Busy','ST7_A_Dis2_End','ST7_A_Dis2_M','Station_A_Data[7]'])
refs=[]
for s in p.sections:
    if s['name']==sec['name']:continue
    for i,r in enumerate(s['rows']):
        if any(t in json.dumps(r,ensure_ascii=False) for t in tags):refs.append({'section':s['name'],'row':i,'rung':r,'compact':compact(r)})
sm.save_json(b/'references.json',refs)
vlines=[line for txt in p.variable_parts.values() for line in txt.splitlines() if any(x in line for x in ['A_SF_CT','ST7_A_Dis2','RCON1_5','RCON1_4','CYw_SH_A','StackPitch','In_Sen_SH'])]
(b/'variables.txt').write_text('\n'.join(vlines),encoding='utf-8')
print(json.dumps({'versions':comparison,'selected':m['name'],'rows':len(sec['rows']),'references':[(x['section'],x['row']) for x in refs]},ensure_ascii=False,indent=2))
print('\n'.join(lines))
