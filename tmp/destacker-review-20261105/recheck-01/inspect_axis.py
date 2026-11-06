from pathlib import Path
import json,re
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'));s={x['name']:x['rows'] for x in d['sections']}
for i,r in enumerate(s['RCON_IAI']):
    names=[c.get('Var','') for c in r['CLs']]
    if not (any(n.startswith('RCON2_2_M[') for n in names) or (any(n.startswith('RCON2_2_MoveDone') for n in names))):continue
    print('ROW',i,r.get('CMT','').replace('\r\n',' / '))
    for c in r['CLs']:
        if c['__type']=='HL':continue
        x={k:c[k] for k in ['__type','Var','Name','Not','X','Y','S','R','P','Type'] if k in c}
        for io in ['In','Out']:
            if c.get(io):x[io]=[(p.get('Arg'),p.get('Var')) for p in c[io] if p.get('Var')]
        print(json.dumps(x,ensure_ascii=False))
    print('VL',r['VLs'])
for needle in ['Destacker_M','RCON2_1_M','RCON2_1_IN_PositionDone','RCON2_1_MoveDone','P_Off']:
    for content in d['variable_parts'].values():
        for ln in content.splitlines():
            if f'\tN={needle}\t' in ln and '\tG=VAR_GLOBAL' in ln:print('VAR',ln)
print('M26_REFS',[(name,i,c.get('Var')) for name,rows in s.items() for i,r in enumerate(rows) for c in r['CLs'] if c.get('Var')=='Destacker_M[26]'])
