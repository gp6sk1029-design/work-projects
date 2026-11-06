"""生成した段バラシ29行の配線条件を検算する。実PLC・実通信の検証ではない。"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import product
import sys,json,re
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;m=json.loads((b/'build.json').read_text(encoding='utf-8'));stage=json.loads((b/'stage.json').read_text(encoding='utf-8'))
p=sm.Project(stage['candidate']);data=json.loads((b/'project.json').read_text(encoding='utf-8'));sec=p.section('Destacker_段バラシ');rows=sec['rows']
src=(b.parent/'box-cycle-implement-20261105/check_conditions.py').read_text(encoding='utf-8')
ns={'defaultdict':defaultdict,'re':re};exec(src[src.index('class Model:'):src.index('\nresults=[]')],ns);Model=ns['Model']
M=lambda n:f'Destacker_M[{n}]';Done='RCON2_1_MoveDone';Busy='Destacker_Init_Busy'
mp={int(k):v for k,v in m['old_to_new'].items()};gp={int(k):v for k,v in m['guard_rows'].items()};results=[]

# 新補助回路と完了待ちの全組合せ。自己保持枝を余計に遮断していないことも検査。
target_state={5:(8,9),6:(9,10),8:(11,12),13:(17,18),16:(22,23),18:(24,25)}
cases=0
for step,guard,target,label in m['spec']:
    end,next_stage=target_state[target]
    for active,done,previous,held,release in product([False,True],repeat=5):
        for safe_a,safe_b in (product([False,True],repeat=2) if target==8 else [(False,False)]):
            env={M(step):active,Done:done,M(guard):previous,M(end):held,M(next_stage):release,M(3):safe_a,M(4):safe_b}
            a=Model(env);a.row(rows[gp[target]])
            expect_guard=active and ((not done) or previous)
            assert a.env[M(guard)]==expect_guard
            a.row(rows[mp[target]])
            expected=(active and expect_guard and done or held or (target==8 and safe_a and safe_b)) and not release
            assert a.env[M(end)]==expected,(target,env,dict(a.env),expected)
            cases+=1
results.append({'test':'6移動のDone OFF確認と完了待ち・自己保持','cases':cases})

for auto,busy,held,m2,finished in product([False,True],repeat=5):
    a=Model({'Auto_Com_Start':auto,Busy:busy,M(1):held,M(2):m2,M(26):finished});a.row(rows[mp[0]])
    assert a.env[M(1)]==(((auto and not busy) or held) and not m2 and not finished)
results.append({'test':'初回開始のBusy/完了共通条件','cases':32})
for start,prior,finished in product([False,True],repeat=3):
    a=Model({M(1):start,Busy:prior,M(26):finished});a.row(rows[m['busy_row']]);assert a.env[Busy]==((start or prior) and not finished)
results.append({'test':'初回Busyの保持と解除','cases':8})
for initial,accepted,home,held in product([False,True],repeat=4):
    a=Model({M(11):initial,M(12):accepted,'Out_CYw_Empty_Container_CY_H_Done':home,M(26):held});a.row(rows[m['done_row']])
    assert a.env[M(26)]==((initial and accepted and home) or held)
results.append({'test':'初回から通常への受渡し後に初回済みを保持','cases':16})
for oldidx in [0,1,2]:
    a=Model({'Auto_Com_Start':True,M(1):True,M(2):True,M(3):True,M(26):True,'Out_CYw_Sep_Claw_F_Done':True})
    a.row(rows[mp[oldidx]]);assert not a.env[M(oldidx+1)]
results.append({'test':'初回済みで開始・爪保持・判定を解除','cases':3})

# ユーザーの修正を保全。今回不要な行はJSONフィールドまで一致。
unchanged=[3,4,7,9,10,11,12,14,15,17,19,20]
for i in unchanged:assert rows[mp[i]]==m['source_user_rows'][i]
for before,after in sm.align(sm.Project(m['source_external']),p):
    if before['name']!='Destacker_段バラシ':assert before['rows']==after['rows']
coils=Counter(c['Var'] for rr in rows for c in rr['CLs'] if c['__type']=='ST' and re.fullmatch(r'Destacker_M\[\d+\]',c.get('Var','')))
assert set(coils)=={M(i) for i in range(1,33)} and all(n==1 for n in coils.values())
results.append({'test':'既存工程番号保持・ユーザー修正12行保全・他24節不変・M1～32各1コイル','cases':1})

def cycle_model(pos,two_stages,axis_delay,cyl_delay,done_hold,initial_wait):
    a=Model({'Auto_Com_Start':True,'RCON2_1_ActualPos_mm':pos,'HMI_RCON2_1_OUT_TargetPos[1]':0,'HMI_RCON2_1_OUT_TargetPos[2]':100,'HMI_RCON2_1_OUT_TargetPos[3]':200,
        'RCON2_5_ActualPos_mm':0,'HMI_RCON2_5_OUT_TargetPos[1]':0,'TimerQ_In_Sen_Container_Direction_Check':True,'TimerQ_In_Sen_Destacker_Stage_01_Exist':True,
        'TimerQ_In_Sen_Destacker_Stage_02_Exist':two_stages,'TimerQ_In_SenCY_Empty_Container_CY_H':True,'TimerQ_In_Sen_Supply_Container_Exist':initial_wait>0})
    e=a.env;pending=[];expires={};prev={};events=[];ends=0;inits=0;entries=0;finished=False
    commands=[c['Var'] for rr in rows for c in rr['CLs'] if c['__type']=='ST' and re.fullmatch(r'(RCON2_1_Auto|Out_CYw_.+_Auto)\[\d+\]',c.get('Var',''))]
    for tick in range(3500):
        if tick==initial_wait:e['TimerQ_In_Sen_Supply_Container_Exist']=False
        for tag,at in list(expires.items()):
            if tick>=at:e[tag]=False;del expires[tag]
        for at,tag,cmd,posval in list(pending):
            if tick!=at:continue
            pending.remove((at,tag,cmd,posval));e[tag]=True;expires[tag]=tick+done_hold
            if cmd.startswith('RCON2_1_Auto'):
                e['RCON2_1_ActualPos_mm']=posval
                if cmd=='RCON2_1_Auto[4]':e['TimerQ_In_Sen_Supply_Container_Exist']=True
            elif cmd.startswith('Out_CYw_Empty_Container_CY_F_Auto'):
                e['TimerQ_In_SenCY_Empty_Container_CY_H']=False;e['TimerQ_In_Sen_Container_Arrival']=True;e['TimerQ_In_Sen_Supply_Container_Exist']=False
            elif cmd.startswith('Out_CYw_Empty_Container_CY_H_Auto'):e['TimerQ_In_SenCY_Empty_Container_CY_H']=True
        before=dict(e)
        for rr in rows:a.row(rr)
        if e[M(2)] and not before.get(M(2)):inits+=1
        if e[M(12)] and not before.get(M(12)):entries+=1
        if e['Destacker_End'] and not before.get('Destacker_End'):ends+=1;events.append([tick,'段バラシ完了',ends])
        if e[M(26)]:finished=True
        if finished:assert not any(e[M(n)] for n in [1,2,3]),('初回再進入',tick)
        for cmd in commands:
            now=bool(e[cmd]);prior=prev.get(cmd,False);prev[cmd]=now
            if now and not prior:
                axis=cmd.startswith('RCON2_1_Auto')
                tag=Done if axis else re.sub(r'_Auto\[\d+\]$','_Done',cmd)
                # 受け側・実機の代わりに、要求後かつ前完了解除後の完了入力を外部供給する。
                at=max(tick+axis_delay,expires.get(Done,tick)+axis_delay) if axis else tick+cyl_delay
                pending.append((at,tag,cmd,e['RCON2_1_OUT_TargetPos_mm'] if axis else None))
        if ends>=3 and entries>=4:
            assert inits==1 and e[M(26)] and not e[Busy]
            return {'initial_position':pos,'two_stages':two_stages,'axis_delay':axis_delay,'cyl_delay':cyl_delay,'done_hold':done_hold,'initial_wait':initial_wait,'model_scans':tick+1,'initial_runs':inits,'ends':ends,'entries':entries}
    (b/'failed_cycle.json').write_text(json.dumps({'events':events,'env':dict(e),'pending':pending},ensure_ascii=False,indent=2),encoding='utf-8')
    raise AssertionError(('モデル未完了',pos,two_stages,axis_delay,cyl_delay,done_hold,events[-5:]))

runs=[]
for pos,two,hold,wait in product([0,50],[False,True],[1,10],[0,5]):runs.append(cycle_model(pos,two,3,5,hold,wait))
results.append({'test':'初回1回→段バラシ3サイクル→次入口の条件モデル','cases':len(runs),'scope':'全29行。軸・シリンダの完了とセンサー変化は外部供給。RCON受け側・Output駆動・通信・実機の結合モデルではない。'})
report={'candidate_sha':p.fingerprint,'results':results,'runs':runs,'full_application_build':False,'plc_simulation':False,'machine_test':False}
sm.save_json(b/'conditions.json',report);print(json.dumps({'results':results,'cycle_runs':len(runs)},ensure_ascii=False))
