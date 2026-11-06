from pathlib import Path
import json,re
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'));s={x['name']:x['rows'] for x in d['sections']}
for name,ii in [('RCON_IAI',range(243,248)),('Output_出力',[268,271,274,277]),('AutoMode_自動運転',[3]),('Error_エラー処理',[36]),('Destacker_段バラシ',[11,18,19])]:
    for i in ii:
        r=s[name][i]
        print(name,i,r.get('CMT','').replace('\r\n',' / '))
        for c in r['CLs']:
            if c['__type']=='HL':continue
            z={k:c[k] for k in ['__type','Var','Name','Not','X','Y','Id'] if k in c}
            for io in ['In','Out']:
                if c.get(io):z[io]=[(p.get('Arg'),p.get('Var')) for p in c[io] if p.get('Var')]
            print(json.dumps(z,ensure_ascii=False))
        if name.startswith('Destacker'):print('VL',r['VLs'])
for tag in ['RCON2_1_OUT_TargetPos_mm','RCON2_1_ActualPos_mm','Destacker_End','Destacker_Error','Retry[13]']:
    print('WRITERS',tag)
    for name,rows in s.items():
        for i,r in enumerate(rows):
            if any((c['__type']=='ST' and c.get('Var')==tag) or any(p.get('Var')==tag for p in c.get('Out',[])) for c in r['CLs']):print(name,i)
variables={}
for content in d['variable_parts'].values():
    for ln in content.splitlines():
        if ln.startswith('++D='):
            f=dict(p.split('=',1) for p in ln[2:].split('\t') if '=' in p)
            if f.get('G')=='VAR_GLOBAL':variables[f['N']]=f
for tag in ['HMI_RCON2_1_OUT_TargetPos','HMI_RCON2_5_OUT_TargetPos','Out_CYw_Empty_Container_CY_H','Out_CYw_Empty_Container_CY_F','Out_CYw_Sep_Claw_H','Out_CYw_Sep_Claw_F','RCON2_1_ActualPos_mm']:
    print('VARIABLE',tag,variables.get(tag))
