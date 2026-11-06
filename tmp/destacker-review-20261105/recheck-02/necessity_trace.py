"""M2有無の同一入力に対する反例。保存回路の条件モデルであり実機ではない。"""
from pathlib import Path
from collections import defaultdict
import json,re,sys,copy
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;p=sm.Project('C:/OMRON/Data/Solution/fe78558c-1d0e-41d5-9b83-730179a87edb')
r=p.section('RCON_IAI')['rows']
src=(b.parent.parent/'box-cycle-implement-20261105/check_conditions.py').read_text(encoding='utf-8')
ns={'defaultdict':defaultdict,'re':re};exec(src[src.index('class Model:'):src.index('\nresults=[]')],ns);Model=ns['Model']
def run(use_memory):
    env={'P_On':True,'AutoMode':True,'RCON2_CommOK':True,'RCON2_WriteEnable':True,'RCON2_LayoutConfirmed':True,'RCON2_ByteOrderConfirmed':True,
    'RCON2_AxisApply[2]':True,'RCON2_MotionPermit[2]':True,'RCON2_IN[2].DataValid':True,'RCON2_EncodeOK[2]':True,'RCON2_2_Ready':True,
    'RCON2_2_OUT_Speed_mm_s':100.,'RCON2_2_OUT_AccDec_G':.3,'RCON2_2_OUT_PositionBand_mm':.1,'RCON2_2_Auto[1]':True,'RCON2_2_IN_PositionDone':True}
    q=copy.deepcopy(r[324])
    if not use_memory:
        for c in q['CLs']:
            if c['__type']=='LD' and c.get('Var')=='RCON2_2_M[2]':c['__type']='HL';c.pop('Var')
    a=Model(env);e=a.env;pending=[];events=[];prev={};first_start=None;first_done=None
    for tick in range(40):
        for at,val in list(pending):
            if tick==at:e['RCON2_2_IN_PositionDone']=val;pending.remove((at,val))
        a.row(r[283]);a.row(r[289]);a.row(r[322])
        if use_memory:a.row(r[323])
        a.row(q)
        tags=['RCON2_2_M[1]','RCON2_2_M[2]','RCON2_2_IN_PositionDone','RCON2_OUT[2].Control.Start','RCON2_2_MoveDone']
        state={k:bool(e[k]) for k in tags}
        if state!=prev:events.append({'model_ms':tick*10,**state})
        if state['RCON2_OUT[2].Control.Start'] and first_start is None:
            first_start=tick*10;pending.extend([(tick+2,False),(tick+18,True)])
        if state['RCON2_2_MoveDone'] and first_done is None:first_done=tick*10
        prev=state
        if first_start is not None and first_done is not None:break
    return {'memory':use_memory,'first_Start_ms':first_start,'first_Done_ms':first_done,'events':events}
without=run(False);with_memory=run(True)
assert without['first_Done_ms']<without['first_Start_ms'],without
assert with_memory['first_Done_ms']>with_memory['first_Start_ms'],with_memory
o={'without_M2':without,'with_M2':with_memory,'scope':'対象283/289/322/323/324の保存配線条件モデル。10msは検算刻みで実PLC周期・通信遅延の測定値ではない。許可成立とPEND初期ONを仮定。実機反応の遅延は比較用外部入力。','source_sha':p.fingerprint,'source_unchanged':p.current_fingerprint()==p.fingerprint}
(b/'necessity_trace.json').write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(o,ensure_ascii=False))
