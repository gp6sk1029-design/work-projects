"""保存ラダーから条件例を検算する。PLCの実行・実機シミュレーションではない。"""
from pathlib import Path
import json,re
from collections import defaultdict
b=Path(__file__).parent
d=json.loads((b/'project.json').read_text(encoding='utf-8'))
s={x['name']:x['rows'] for x in d['sections']}
source=(b.parent/'box-cycle-implement-20261105/check_conditions.py').read_text(encoding='utf-8')
ns={'defaultdict':defaultdict,'re':re}
exec(source[source.index('class Model:'):source.index('\nresults=[]')],ns)
Model=ns['Model'];dest=s['Destacker_段バラシ'];M=lambda i:f'Destacker_M[{i}]'
result=[]
def record(name,model,keys,note=''):
    v={k:model.env[k] for k in keys}
    result.append({'case':name,'observed':v,'limit':note})

# 判定中M14からM15なしで移動要求が出る。
a=Model({M(14):True,M(15):False,'HMI_RCON2_1_OUT_TargetPos[2]':123.0})
a.row(dest[12]);assert a.env[M(16)] and a.env['RCON2_1_Auto[5]']
record('判定OKがOFFでも12行目で移動要求',a,[M(14),M(15),M(16),'RCON2_1_Auto[5]','RCON2_1_OUT_TargetPos_mm'])

# 初回の安全位置復帰要求に目標値転送がなく、完了待ちもしない。
a=Model({M(9):True,'Out_CYw_Sep_Claw_F_Done':True,'RCON2_1_MoveDone':False,'RCON2_1_OUT_TargetPos_mm':123.0})
a.row(dest[7]);a.row(dest[8])
assert a.env[M(10)] and a.env[M(11)] and a.env['RCON2_1_OUT_TargetPos_mm']==123.0
record('7→8行目は軸完了OFFでも初回完了へ進む',a,[M(10),M(11),'RCON2_1_Auto[3]','RCON2_1_MoveDone','RCON2_1_OUT_TargetPos_mm'])
a.row(dest[7]);assert not a.env['RCON2_1_Auto[3]']
record('次走査でAuto3は解除',a,['RCON2_1_Auto[3]'], 'RCON受け側の100ms連続ONに達しない1走査の要求になり得る')

# 既存完了信号を次の移動要求と同じ走査で使う。
a=Model({M(7):True,'RCON2_1_MoveDone':True,'HMI_RCON2_1_OUT_TargetPos[2]':123.0})
a.row(dest[5]);a.row(dest[6]);assert a.env[M(8)] and a.env[M(9)]
record('5→6行目が同じ旧完了ONで連続成立',a,[M(8),M(9),'RCON2_1_Auto[2]','Out_CYw_Sep_Claw_F_Auto[2]'], '次指令の実到着ではなく、直前指令の100ms保持完了を使用する条件例')

# 正常な送り戻り完了時にX1010がONであれば、繰返し入口が閉じる。
a=Model({'Output_Share_M[1]':True,'TimerQ_In_SenCY_Empty_Container_CY_H':True,M(25):True,'TimerQ_In_Sen_Supply_Container_Exist':False})
a.row(s['Output_出力'][269]);a.row(dest[20]);a.row(dest[9])
assert a.env['Destacker_End'] and not a.env[M(12)]
record('20→9行目の繰返し入口が戻りセンサONで不成立',a,['Out_CYw_Empty_Container_CY_H_Done','TimerQ_In_SenCY_Empty_Container_CY_H','Destacker_End',M(12)], '外部からX1010をOFFにする動作が別途ない条件。初回枝はこの例ではOFF')

# 初回済みの記憶がなく、供給センサOFF時に開始枝が再成立。
a=Model({'Auto_Com_Start':True,'TimerQ_In_Sen_Supply_Container_Exist':False,M(17):True})
a.row(dest[0]);a.row(dest[1]);assert a.env[M(2)]
record('通常の爪戻り工程中でも初回枝が再成立',a,[M(17),M(1),M(2),'Out_CYw_Sep_Claw_F_Auto[1]'], 'Auto_Com_StartがONで初回M2/M3がOFFの場合。物理出力は受け側条件で別途制限')

# 11行目は送り戻りDoneではなく爪戻りDone。初回Up枝がこれを迂回。
a=Model({M(13):True,'Retry[13]':False,'Out_CYw_Sep_Claw_H_Done':False,'Out_CYw_Empty_Container_CY_H_Done':False})
a.row(dest[11]);assert a.env[M(14)]
record('11行目は両方の戻りDoneがOFFでもM14成立',a,[M(13),M(14),'Out_CYw_Sep_Claw_H_Done','Out_CYw_Empty_Container_CY_H_Done'], 'Retry[13]の否定接点＋Upによる初回迂回枝')

# センサ成功条件と戻りセンサの関係。
for home in [False,True]:
    a=Model({M(13):True,'Retry[13]':False,'TimerQ_In_SenCY_Empty_Container_CY_H':home,'TimerQ_In_Sen_Container_Direction_Check':True,'TimerQ_In_Sen_Destacker_Stage_01_Exist':True})
    a.row(dest[11]);assert a.env[M(15)]== (not home)
    record(f'11行目確認OKとX1010={home}',a,[M(14),M(15),'TimerQ_In_SenCY_Empty_Container_CY_H'])

# 要求番号を切り替えてもOR全体の立上りは再発しない。
a=Model({'RCON2_1_Auto[1]':True,'RCON2_1_Ready':True})
for _ in range(12):a.row(s['RCON_IAI'][281])
assert a.env['RCON2_1_M[1]']
a.env['RCON2_1_MoveDone']=True;a.row(s['RCON_IAI'][281])
a.env['RCON2_1_Auto[1]']=False;a.env['RCON2_1_Auto[2]']=True
a.env['RCON2_1_MoveDone']=False
for _ in range(12):a.row(s['RCON_IAI'][281])
assert not a.env['RCON2_1_M[1]']
record('Auto1からAuto2への連続切替を受け側が再受付しない',a,['RCON2_1_Auto[1]','RCON2_1_Auto[2]','RCON2_1_TON[1].Q','RCON2_1_M[1]'], 'RCON_IAI281行目のOR全体が途中でOFFにならない条件。P_Off解除とは独立した問題')

# 全自動要求の生成元と受け側の接点数。
refs=[]
for r in dest:
    for c in r['CLs']:
        if c['__type']=='ST' and re.fullmatch(r'(RCON2_1_Auto|Out_CYw_.+_Auto)\[\d+\]',c.get('Var','')):
            tag=c['Var'];consumers=[(name,i) for name,rows in s.items() if name!='Destacker_段バラシ' for i,row in enumerate(rows) if any(x['__type']=='LD' and x.get('Var')==tag for x in row['CLs'])]
            refs.append({'tag':tag,'consumer_rows':consumers})
assert all(x['consumer_rows'] for x in refs)
coils=[c['Var'] for row in dest for c in row['CLs'] if c['__type']=='ST' and re.fullmatch(r'Destacker_M\[\d+\]',c.get('Var',''))]
assert len(coils)==25 and len(set(coils))==25
out={'scope':'保存済みHのラダー配線条件をモデル化した反例検算。PLC走査時間の実測、Sysmacシミュレータ、物理機器、通信は含まない。','cases':result,'request_consumers':refs,'step_coils':coils}
(b/'counterexamples.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
