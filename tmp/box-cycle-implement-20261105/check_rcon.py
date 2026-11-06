"""RCON追加ラダーを10ms刻みの条件モデルで検査。通信・実機検査ではない。"""
from pathlib import Path
from zipfile import ZipFile
from itertools import product
import json,re
b=Path(__file__).parent
shared=(b/'check_conditions.py').read_text(encoding='utf-8').split('results=[]',1)[0]
exec(compile(shared,str(b/'check_conditions.py'),'exec'))
with ZipFile(m['staged']) as z:rcon=[json.loads(l) for l in z.read(m['rcon_part']).decode('utf-8-sig').splitlines()]
rm={int(k):v for k,v in m['rcon_old_to_new_rows'].items()}
results=[]
def base_env(axis):
    env={'P_On':True,'AutoMode':True,'RCON2_CommOK':True,'RCON2_WriteEnable':True,'RCON2_LayoutConfirmed':True,'RCON2_ByteOrderConfirmed':True,
        f'RCON2_AxisApply[{axis}]':True,f'RCON2_MotionPermit[{axis}]':True,f'RCON2_IN[{axis}].DataValid':True,f'RCON2_EncodeOK[{axis}]':True,
        f'RCON2_{axis}_Ready':True,f'RCON2_{axis}_OUT_Speed_mm_s':100.0,f'RCON2_{axis}_OUT_AccDec_G':0.3,f'RCON2_{axis}_OUT_PositionBand_mm':0.1}
    return env

for axis in range(2,6):
    oldbase=283+(axis-2)*40;permit=rcon[rm[oldbase]-1];start=rcon[rm[oldbase+5]];request=rcon[rm[oldbase+38]];receipt=rcon[rm[oldbase+38]+1];done=rcon[rm[oldbase+39]]
    normal=base_env(axis);sim=Model(normal);sim.row(permit);assert sim.env[f'RCON2_{axis}_M[3]']
    # 各許可を1つずつ遮断し、0速度/0加速/負幅でも不許可になること。
    for tag in ['AutoMode','RCON2_CommOK','RCON2_WriteEnable','RCON2_LayoutConfirmed','RCON2_ByteOrderConfirmed',
        f'RCON2_AxisApply[{axis}]',f'RCON2_MotionPermit[{axis}]',f'RCON2_IN[{axis}].DataValid',f'RCON2_EncodeOK[{axis}]',f'RCON2_{axis}_Ready']:
        env=dict(normal);env[tag]=False;s=Model(env);s.row(permit);assert not s.env[f'RCON2_{axis}_M[3]']
    for tag in ['Pause[1]','M9999','In_Sw_RESET']:
        env=dict(normal);env[tag]=True;s=Model(env);s.row(permit);assert not s.env[f'RCON2_{axis}_M[3]']
    for suffix,value in [('Speed_mm_s',0),('AccDec_G',0),('PositionBand_mm',-0.1)]:
        env=dict(normal);env[f'RCON2_{axis}_OUT_{suffix}']=value;s=Model(env);s.row(permit);assert not s.env[f'RCON2_{axis}_M[3]']
    for active,pend,held in product([False,True],repeat=3):
        s=Model({f'RCON2_{axis}_M[1]':active,f'RCON2_{axis}_IN_PositionDone':pend,f'RCON2_{axis}_M[2]':held})
        s.row(receipt);assert s.env[f'RCON2_{axis}_M[2]']==(active and (not pend or held))
    # 開始前PEND ONを完了としない／完了保持中の次要求を失わない。
    sim=Model(normal);e=sim.env;e[f'RCON2_{axis}_Auto[1]']=True;e[f'RCON2_{axis}_IN_PositionDone']=True
    starts=[];completions=[];prev_start=False;prev_done=False;pending=[];first_pend_off=False
    for tick in range(200):
        for at,value in list(pending):
            if at==tick:
                e[f'RCON2_{axis}_IN_PositionDone']=value;pending.remove((at,value))
                if not value:first_pend_off=True
        sim.row(permit);sim.row(start);sim.row(request);sim.row(receipt);sim.row(done)
        s=bool(e[f'RCON2_OUT[{axis}].Control.Start']);q=bool(e[f'RCON2_{axis}_MoveDone'])
        if s and not prev_start:
            starts.append(tick);pending.extend([(tick+2,False),(tick+18,True)])
        if q and not prev_done:
            assert starts and first_pend_off
            completions.append(tick)
            if len(completions)==1:
                # 要求ORを一度もOFFにせず、要求[1]から[2]へ切り替える。
                e[f'RCON2_{axis}_Auto[1]']=False;e[f'RCON2_{axis}_Auto[2]']=True
            else:e[f'RCON2_{axis}_Auto[2]']=False
        prev_start=s;prev_done=q
    assert len(starts)==2 and len(completions)==2,(axis,starts,completions)
    assert starts[1]>completions[0]+10
    # TOF保持中も許可OFFならStartを直ちにOFFにする。
    s=Model(normal);s.env[f'RCON2_{axis}_M[1]']=True;s.row(permit);s.row(start)
    assert s.env[f'RCON2_OUT[{axis}].Control.Start']
    s.env['Pause[1]']=True;s.row(permit);s.row(start)
    assert not s.env[f'RCON2_OUT[{axis}].Control.Start']
    results.append({'axis':axis,'permission_checks':17,'receipt_cases':8,'start_ticks_10ms':starts,'completion_ticks_10ms':completions,'request_switch_while_OR_on':'pass','pause_cuts_internal_start':'pass'})
report={'axes':results,'source':'生成したRCONラダー','scope':'10ms刻みのTON/TOF・接点条件モデル。実PLC命令・実通信・PEND波形・実機は未検証。既存100msはそのまま。'}
(b/'rcon_conditions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
