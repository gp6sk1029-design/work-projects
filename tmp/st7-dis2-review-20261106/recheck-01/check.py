"""更新3行の実条件と、未変更の主要問題を再検算。"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import product
import json,re,sys
b=Path(__file__).parent;d=json.loads((b/'snapshot.json').read_text(encoding='utf-8'));old=json.loads((b.parent/'snapshot.json').read_text(encoding='utf-8'))
src=(b.parent/'check.py').read_text(encoding='utf-8');ns={'defaultdict':defaultdict,'re':re};exec(src[src.index('class Model:'):src.index('\nchecks=[]')],ns);Model=ns['Model']
s={x['name']:x['rows'] for x in d['sections']};prior={x['name']:x['rows'] for x in old['sections']};rows=s['ST7_A_Dis2_左SF排出'];M=lambda n:f'ST7_A_Dis2_M[{n}]'
results=[]
cases=0
for phase,ok,held,retry,nextphase in product([False,True],repeat=5):
    a=Model({M(17):phase,M(18):ok,M(21):held,'Retry[12]':retry,M(22):nextphase});a.row(rows[15],15)
    assert a.e['Out_CYw_Ejc_Hldr_Feed_A_F_Auto[1]']==(((phase and ok) or held) and not retry and not nextphase);cases+=1
results.append({'item':'15行OK限定の開始・保持・解除','cases':cases,'passed':True})
branch=[]
for choice in [18,19,20]:
    a=Model({M(17):True,M(choice):True,'Out_CYw_Ejc_Hldr_Feed_A_F_Done':False})
    a.row(rows[15],15);a.row(rows[16],16)
    branch.append({'choice':choice,'Y719_request':a.e['Out_CYw_Ejc_Hldr_Feed_A_F_Auto[1]'],'feed_done':False,'horizontal_request':a.e['RCON1_3_Auto[2]']})
assert [x['Y719_request'] for x in branch]==[True,False,False] and all(x['horizontal_request'] for x in branch)
results.append({'item':'15→16行：OKだけ送り指令を出すが、完了OFFでも同一走査で横移動','evidence':branch})
# 推奨：16行のM21接点だけを元の送り行Doneへ戻す。実プロジェクトには書かない。
import copy
proposal=copy.deepcopy(rows[16]);changed=[]
for c in proposal['CLs']:
    if c['__type']=='LD' and c.get('Var')==M(21):c['Var']='Out_CYw_Ejc_Hldr_Feed_A_F_Done';changed.append(c)
assert len(changed)==1
test=[]
for choice,done in product([18,19,20],[False,True]):
    a=Model({M(17):True,M(choice):True,'Out_CYw_Ejc_Hldr_Feed_A_F_Done':done});a.row(rows[15],15);a.row(proposal,16)
    expected=done if choice==18 else True;assert a.e['RCON1_3_Auto[2]']==expected
    test.append({'choice':choice,'feed_done':done,'horizontal_request':a.e['RCON1_3_Auto[2]']})
results.append({'item':'16行1接点差替案：OKだけ完了待ち、NGは迂回を維持','cases':6,'passed':True,'evidence':test})
cases=0
for m3,h,m4,f,held,ack in product([False,True],repeat=6):
    env={'ST7_A_SF_M[3]':m3,'Out_CYw_SH_A_Turn_H_Done':h,'ST7_A_SF_M[4]':m4,'Out_CYw_SH_A_Turn_F_Done':f,'ST7_A_SF_Wait_Pickup':held,'BoxPacking_A_Pickup_Done':ack}
    a=Model(env);z=Model(env);a.row(rows[31],31);z.row(prior['ST7_A_Dis2_左SF排出'][31],31)
    expected=((m3 and h) or (m4 and f) or held) and not ack
    assert a.e['ST7_A_SF_Wait_Pickup']==z.e['ST7_A_SF_Wait_Pickup']==expected;cases+=1
results.append({'item':'31行は接続・論理同一、Ix整理のみ','cases':cases,'passed':True})
a=Model({M(12):True});a.row(rows[10],10);first=a.e['RCON1_5_Auto[2]'];a.row(rows[19],19);assert first and not a.e['RCON1_5_Auto[2]']
results.append({'item':'10/19行Auto2重複は残存','after_10':first,'after_19':a.e['RCON1_5_Auto[2]']})
a=Model({'ST7_A_Dis2_End':True,'Ins_A_Next_Cycle':True});a.row(rows[26],26);assert a.e['ST7_A_Dis2_End'];results.append({'item':'26行EndのNextCycle解除なしは残存','End':True})
a=Model({M(8):True})
for _ in range(8):
    for i in range(8,27):a.row(rows[i],i)
assert a.e[M(10)] and not a.e['ST7_A_Dis2_End'];results.append({'item':'8行無ワークM10から完了経路なしは残存','M10':True,'End':False})
tag='Out_CYw_Ejc_Hldr_Feed_A_H_Auto[3]';receivers=[(name,i) for name,rs in s.items() for i,r in enumerate(rs) for c in r['CLs'] if c['__type']=='LD' and c.get('Var')==tag];assert not receivers
results.append({'item':'25行戻要求Auto3の受け接点なしは残存','receivers':receivers})
sys.path.insert(0,'C:/Users/SEIGI-N13/work-projects/.agents/skills/sysmac-studio/scripts');import sysmac as sm
p=sm.Project(d['path']);assert p.fingerprint==d['sha'],'読取り後にユーザー編集があったため再取得が必要'
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/st7-dis2-review-20261106/recheck-01');out.mkdir(exist_ok=True)
report={'solution':d['solution'],'saved_date':d['date'],'sha256':d['sha'],'original_unchanged_during_review':True,'actual_project_modified':False,'results':results,'full_application_build':False,'machine_test':False}
sm.save_json(out/'検証結果.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
