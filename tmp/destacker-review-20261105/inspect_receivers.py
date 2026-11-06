from pathlib import Path
import json,re
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
sections={s['name']:s['rows'] for s in d['sections']}
for name,indices in [('RCON_IAI',[243,244,245,246,248,263,267,280,281,282]),('Output_出力',range(268,280)),('Error_エラー処理',[36]),('AutoMode_自動運転',[3])]:
    for i in indices:
        r=sections[name][i]
        print(name,i,r.get('CMT','').replace('\r\n',' / '))
        print(json.dumps({'CLs':r['CLs'],'VLs':r['VLs']},ensure_ascii=False))
tags=set()
for r in sections['Destacker_段バラシ']:
    for c in r['CLs']:
        if c['__type']=='LD' and c.get('Var','').startswith('TimerQ_'):tags.add(c['Var'])
print('INPUT_BINDINGS')
inputs=[]
for i,r in enumerate(sections['Input_入力']):
    if any(c.get('Var') in tags and c['__type']=='ST' for c in r['CLs']):
        inputs.append({'row':i,'rung':r})
        print(i,json.dumps(r,ensure_ascii=False))
allvars={}
for part,text in d['variable_parts'].items():
    for line in text.splitlines():
        if not line.startswith('++D='):continue
        f=dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p)
        allvars.setdefault(f['N'],[]).append({'part':part,'fields':f})
wanted=set(tags)|{'Auto_Com_Start','Destacker_M','Destacker_End','Destacker_Error','Retry','Pause','RCON2_1_ActualPos_mm','HMI_RCON2_1_OUT_TargetPos'}
for v in inputs:
    for c in v['rung']['CLs']:
        if c.get('Var'):wanted.add(c['Var'])
bindings={n:allvars[n] for n in sorted(wanted) if n in allvars}
(b/'bindings.json').write_text(json.dumps(bindings,ensure_ascii=False,indent=2),encoding='utf-8')
for n in sorted(wanted):
    if n in allvars:print(n,[(x['fields'].get('Com'),x['fields'].get('AT')) for x in allvars[n] if x['fields'].get('G')=='VAR_GLOBAL'])
