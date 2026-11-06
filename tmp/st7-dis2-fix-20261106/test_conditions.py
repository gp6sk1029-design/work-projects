"""候補ラダーの局所条件・受渡し・繰返しを確認する（メーカーシミュレータではない）。"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import product
import json,re,sys,copy
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;m=json.loads((b/'build.json').read_text(encoding='utf-8'));p=sm.Project(m['stage'])
src=Path('C:/Users/SEIGI-N13/work-projects/tmp/st7-dis2-review-20261106/check.py').read_text(encoding='utf-8');ns={'defaultdict':defaultdict,'re':re};exec(src[src.index('class Model:'):src.index('\nchecks=[]')],ns);Model=ns['Model']
rows=p.section('ST7_A_Dis2_左SF排出')['rows'];rcon=p.section('RCON_IAI')['rows'];mp={int(k):v for k,v in m['old_to_new_rows'].items()};rm={int(k):v for k,v in m['rcon_old_to_new_rows'].items()};M=lambda n:f'ST7_A_Dis2_M[{n}]'
results=[]
def rr(n):return rows[mp[n]]
def cmt(text):return next(r for r in rows if r.get('CMT','').startswith(text))
def runrow(a,r,n):a.row(r,n)
def record(name,cases):results.append({'test':name,'cases':cases,'passed':True})
# 送りのOK限定とユーザー追加の完了接点を維持。
for choice,done in product([18,19,20],[False,True]):
    a=Model({M(17):True,M(choice):True,'Out_CYw_Ejc_Hldr_Feed_A_F_Done':done});a.row(rr(15),15);a.row(rr(16),16)
    assert a.e['Out_CYw_Ejc_Hldr_Feed_A_F_Auto[1]']==(choice==18)
    assert a.e['RCON1_3_Auto[2]']==(done if choice==18 else True)
record('OKだけ送り行・NGは送り不要、OKだけ送り完了待ち',6)
for choice in [24,25,26]:
    a=Model({M(23):True,M(choice):True});a.row(rr(19),19);assert a.e[M(27)],('下降要求の分岐',choice)
record('OK/キズNG/姿NGの下降要求',3)
# 同じ通常コイルを重複していない。
counts=Counter(c['Var'] for r in rows for c in r['CLs'] if c['__type']=='ST' and not c.get('S') and not c.get('RS'))
assert all(v==1 for k,v in counts.items() if k.startswith('RCON1_5_Auto['))
assert {k for k in counts if k.startswith('RCON1_5_Auto[')}=={f'RCON1_5_Auto[{n}]' for n in range(1,6)}
record('上下軸5要求各1コイル',5)
# 有無判定はA側のみ。無ワークならNG満杯でも正常終了。
for sensed,data,full in product([False,True],repeat=3):
    a=Model({M(8):True,'TimerQ_In_Sen_Work_A_Pos_07':sensed,'Station_A_Data[7].Work_On':data,'TimerQ_In_Sen_NG2_Tray_A_Full':full})
    for name in ['【ワーク有：正常】','【ワーク無：正常】','【ワーク不一致・NG満杯】']:a.row(cmt(name),name)
    assert a.e[M(9)]==(sensed and data and not full)
    assert a.e[M(10)]==(not sensed and not data)
    assert bool(a.e[M(11)])==((sensed!=data) or (full and (sensed or data)))
    a.row(rr(26),26);assert a.e['ST7_A_Dis2_End']==(not sensed and not data)
record('A側有無・満杯・空ワーク完了',8)
for phase,guard,target,axis,label in m['guard_spec']:
    gr=rows[int(m['guard_rows'][str(target)])];done=f'RCON1_{axis}_MoveDone';a=Model({M(phase):True,done:True})
    a.row(gr,'guard');assert not a.e[M(guard)]
    a.e[done]=False;a.row(gr,'guard');assert a.e[M(guard)]
    a.e[done]=True;a.row(gr,'guard');assert a.e[M(guard)]
    a.e[M(phase)]=False;a.row(gr,'guard');assert not a.e[M(guard)]
record('8移動のDone OFF記憶・保持・工程終了で解除',32)
# 配置目標：共通設定禁止が全下降枝へ効く。
for choice,error,busy in product([1,4,5],[False,True],[False,True]):
    vals={M(23):True,'Station_A_Data[7].Total_Judge':1 if choice==1 else 9,'Station_A_Data[7].Judgment_Details':choice,'A_SF_CT':2,'A_SF_StackTarget_mm':180.,'HMI_RCON1_5_OUT_TargetPos[7]':250.,'HMI_RCON1_5_OUT_TargetPos[8]':300.,M(43):error,'ST7_A_SF_Busy':busy}
    a=Model(vals);a.row(rr(18),18)
    flag=M(24 if choice==1 else 25 if choice==4 else 26)
    assert bool(a.e[flag])==(not error and not busy),(choice,error,busy,flag,a.e[flag])
record('全下降枝の設定異常/回転中禁止',12)
for already,count in [(False,0),(False,4),(True,1),(True,5)]:
    a=Model({M(8):True,M(9):True,M(42):already,'A_SF_CT':count,'Station_A_Data[7].Total_Judge':1,'HMI_A_SF_StackPitch_mm':-10.})
    a.row(cmt('【取出し開始の許可】'),'permit');assert a.e[M(45)]
record('初回と再試行の段数許可',4)
# 加算済みはRetryで保持し、次サイクルでのみ解除。
a=Model({M(16):True,M(37):True,'RCON1_5_MoveDone':True,'Station_A_Data[7].Total_Judge':1,'A_SF_CT':0})
for retry in [False,True,False]:
    a.e['Retry[12]']=retry;a.row(rr(14),14);a.row(cmt('【今回ワークの加算済み】'),'count')
assert a.e['A_SF_CT']==1 and a.e[M(42)]
a.e['Ins_A_Next_Cycle']=True;a.row(cmt('【次ワークの加算準備】'),'next');assert not a.e[M(42)]
record('同一ワークRetryでも加算1回',4)
for n in [0,1,2,3,4,5,6]:
    a=Model({'A_SF_CT':n,'HMI_A_SF_StackPitch_mm':-10.,'HMI_RCON1_5_OUT_TargetPos[3]':200.});a.row(rr(17),17)
    assert a.e['A_SF_StackTarget_mm']==200.-10.*(n-1)
record('基準3とピッチ計算',7)
for held,nxt,retry in product([False,True],repeat=3):
    a=Model({'ST7_A_Dis2_End':held,'Ins_A_Next_Cycle':nxt,'Retry[12]':retry});a.row(rr(26),26);assert a.e['ST7_A_Dis2_End']==(held and not nxt and not retry)
record('End保持とNext解除',8)
# 受け側：初期PEND ONのままでは完了しない。新しいOFF/ON後のみ完了。
for axis,start,finish in [(3,120,121),(5,201,202)]:
    phase=f'RCON1_{axis}_M[1]';seen=f'RCON1_{axis}_M[2]';done=f'RCON1_{axis}_MoveDone';pend=f'RCON1_{axis}_IN_PositionDone';rs=[rcon[rm[start]],rcon[rm[finish]-1],rcon[rm[finish]]]
    a=Model({f'RCON1_{axis}_Auto[1]':True,f'RCON1_{axis}_Ready':True,pend:True})
    for _ in range(25):
        for i,r in enumerate(rs):a.row(r,'rcon'+str(i))
        assert not a.e[done]
    assert a.e[phase]
    a.e[pend]=False
    for i,r in enumerate(rs):a.row(r,'rcon'+str(i))
    assert a.e[seen]
    a.e[pend]=True
    for i,r in enumerate(rs):a.row(r,'rcon'+str(i))
    assert a.e[done]
record('RCON2軸の今回PEND OFF/ON確認',2)
for axis,start,finish in [(3,120,121),(5,201,202)]:
    phase=f'RCON1_{axis}_M[1]';done=f'RCON1_{axis}_MoveDone';pend=f'RCON1_{axis}_IN_PositionDone';rs=[rcon[rm[start]],rcon[rm[finish]-1],rcon[rm[finish]]]
    a=Model({f'RCON1_{axis}_Auto[1]':True,f'RCON1_{axis}_Ready':True,pend:True});accepted=[];events=[];last=False
    for tick in range(150):
        for t,v in events[:]:
            if t==tick:a.e[pend]=v;events.remove((t,v))
        for i,r in enumerate(rs):a.row(r,'rcon'+str(i))
        if a.e[phase] and not last:accepted.append(tick);events.extend([(tick+2,False),(tick+8,True)])
        last=bool(a.e[phase])
        if len(accepted)==1 and a.e[done]:a.e[f'RCON1_{axis}_Auto[1]']=False;a.e[f'RCON1_{axis}_Auto[2]']=True
        if len(accepted)==2 and a.e[done]:a.e[f'RCON1_{axis}_Auto[2]']=False
    assert len(accepted)==2,(axis,accepted)
record('要求ORが連続でも2移動を再受付',2)
sm.save_json(b/'conditions.json',{'candidate_sha':p.fingerprint,'results':results,'scope':'局所条件モデル。10msは仮刻み。実出力P_Offは維持したまま内部受付を検算。全体ビルド/実機ではない。'})
print(json.dumps({'tests':len(results),'cases':sum(x['cases'] for x in results),'passed':True},ensure_ascii=False))
