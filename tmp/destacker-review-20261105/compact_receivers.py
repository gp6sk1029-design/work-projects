from pathlib import Path
import json
b=Path(__file__).parent
d=json.loads((b/'project.json').read_text(encoding='utf-8'))
s={x['name']:x['rows'] for x in d['sections']}
def show(name, indices):
    for i in indices:
        r=s[name][i]
        print(name,i,r.get('CMT','').replace('\r\n',' / '))
        for c in r['CLs']:
            if c['__type']=='HL':continue
            z={k:c[k] for k in ['__type','Var','Name','Not','X','Y'] if k in c}
            for io in ['In','Out']:
                if c.get(io):z[io]=[(p.get('Arg'),p.get('Var')) for p in c[io] if p.get('Var')]
            print(json.dumps(z,ensure_ascii=False))
        print('VL',r['VLs'])
show('Output_出力',[269,272,275,278])
show('RCON_IAI',[248,263,280,281,282])
tags={'TimerQ_In_Sen_Supply_Container_Exist','TimerQ_In_SenCY_Empty_Container_CY_H','TimerQ_In_Sen_Container_Direction_Check','TimerQ_In_Sen_Destacker_Stage_01_Exist','TimerQ_In_Sen_Destacker_Stage_02_Exist','TimerQ_In_Sen_Container_Arrival'}
show('Input_入力',[i for i,r in enumerate(s['Input_入力']) if any(c.get('Var') in tags and c['__type']=='ST' for c in r['CLs'])])
bindings=json.loads((b/'bindings.json').read_text(encoding='utf-8'))
for n,parts in bindings.items():
    print('BIND',n,[(v['fields'].get('Com'),v['fields'].get('AT')) for v in parts if v['fields'].get('G')=='VAR_GLOBAL'])
