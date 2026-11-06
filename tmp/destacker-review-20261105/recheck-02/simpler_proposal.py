"""既存TON/自己保持を保ち、PEND単独の立上りで完了を見る案を検算。実データ未変更。"""
from pathlib import Path
from collections import defaultdict
import json,re,copy,sys
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;p=sm.Project('C:/OMRON/Data/Solution/fe78558c-1d0e-41d5-9b83-730179a87edb');rows=p.section('RCON_IAI')['rows']
src=(b.parent.parent/'box-cycle-implement-20261105/check_conditions.py').read_text(encoding='utf-8')
ns={'defaultdict':defaultdict,'re':re};exec(src[src.index('class Model:'):src.index('\nresults=[]')],ns);Model=ns['Model']
req=copy.deepcopy(rows[322]);comp=copy.deepcopy(rows[324])
# 322：PEND NOをTON前に挿入。自己保持側はこの接点を迂回する。
for c in req['CLs']:
    if c.get('X',0)>=4:c['X']=c.get('X',0)+1
for v in req['VLs']:
    if v.get('X',0)>=4:v['X']+=1
req['CLs'].append({'__type':'LD','X':4,'Y':0,'Var':'RCON2_2_IN_PositionDone','Id':'proposal-pend-ready'})
req['CLs'].append({'__type':'HL','X':4,'Y':3})
# 324：M2の列を除去し、PEND→Up→M1の順へ。
cs=[]
for c in comp['CLs']:
    if c.get('X',0)==1:continue
    if c.get('X',0)>1:c['X']-=1
    if c['__type']=='LD' and c.get('Var')=='RCON2_2_M[1]':c['X']=2
    elif c['__type']=='LD' and c.get('Var')=='RCON2_2_IN_PositionDone':c['X']=0
    elif c['__type']=='F' and c.get('Name')=='Up':c['X']=1
    cs.append(c)
comp['CLs']=cs
for v in comp['VLs']:
    if v.get('X',0)>1:v['X']-=1
assert not any(c.get('Var')=='RCON2_2_M[2]' for r in [req,comp] for c in r['CLs'])

def base():return {'P_On':True,'AutoMode':True,'RCON2_CommOK':True,'RCON2_WriteEnable':True,'RCON2_LayoutConfirmed':True,'RCON2_ByteOrderConfirmed':True,
 'RCON2_AxisApply[2]':True,'RCON2_MotionPermit[2]':True,'RCON2_IN[2].DataValid':True,'RCON2_EncodeOK[2]':True,'RCON2_2_Ready':True,
 'RCON2_2_OUT_Speed_mm_s':100.,'RCON2_2_OUT_AccDec_G':.3,'RCON2_2_OUT_PositionBand_mm':.1,'RCON2_2_Auto[1]':True,'RCON2_2_IN_PositionDone':True}
def test(initial_pend,off_delay,on_delay,wait_pend_at=None,never_off=False):
    env=base();env['RCON2_2_IN_PositionDone']=initial_pend;a=Model(env);e=a.env
    pending=[];starts=[];done=[];prev_s=False;prev_d=False;events=[]
    for tick in range(250):
        if tick==wait_pend_at:e['RCON2_2_IN_PositionDone']=True
        for at,val in list(pending):
            if at==tick:e['RCON2_2_IN_PositionDone']=val;pending.remove((at,val))
        for r in [rows[283],rows[289],req,comp]:a.row(r)
        start=bool(e['RCON2_OUT[2].Control.Start']);finish=bool(e['RCON2_2_MoveDone'])
        if start and not prev_s:
            starts.append(tick)
            if not never_off:pending.extend([(tick+off_delay,False),(tick+on_delay,True)])
        if finish and not prev_d:
            assert starts and tick>starts[-1]
            done.append(tick)
            if len(done)==1:
                e['RCON2_2_Auto[1]']=False;e['RCON2_2_Auto[2]']=True
            else:e['RCON2_2_Auto[2]']=False
        if (start!=prev_s) or (finish!=prev_d):events.append([tick,start,finish])
        prev_s=start;prev_d=finish
    if never_off:assert len(starts)==1 and len(done)==0
    elif not initial_pend and wait_pend_at is None:assert not starts and not done
    else:
        assert len(starts)==len(done)==2,(starts,done,events)
        assert starts[1]>done[0]+10
        if wait_pend_at is not None:assert starts[0]>=wait_pend_at+10
    return {'initial_pend':initial_pend,'wait_pend_at':wait_pend_at,'off_delay':off_delay,'on_delay':on_delay,'never_off':never_off,'start_ticks':starts,'done_ticks':done}
runs=[]
for off_delay,on_delay in [(1,15),(2,18),(5,25)]:
    runs.append(test(True,off_delay,on_delay))
    runs.append(test(False,off_delay,on_delay,wait_pend_at=30))
runs.append(test(False,2,18))
runs.append(test(True,2,18,never_off=True))
# 受付待ちの途中にPENDが落ちた場合、TONもやり直す。
a=Model(base());e=a.env
for _ in range(8):
    for r in [rows[283],rows[289],req,comp]:a.row(r)
e['RCON2_2_IN_PositionDone']=False
for r in [rows[283],rows[289],req,comp]:a.row(r)
assert not e['RCON2_2_M[1]'] and not e['RCON2_2_MoveDone']
e['RCON2_2_IN_PositionDone']=True
for _ in range(8):
    for r in [rows[283],rows[289],req,comp]:a.row(r)
    assert not e['RCON2_2_M[1]'] and not e['RCON2_2_MoveDone']
report={'source_sha':p.fingerprint,'source_unchanged':p.current_fingerprint()==p.fingerprint,'runs':runs,'additional_case':'受付中PEND OFFでTONリセット、再ON直後にはM1/Doneを出さない','assumptions':['PEND ONを100ms確認してから新規受付する運転に限定','完了判定行はM1 OFF時も毎走査実行し、UpをPEND単独へ接続','起動/再開時のM1とDoneはOFFへ初期化','通信とPENDの実機応答は未確認'],'scope':'X軸の受付/Start/完了の限定モデル。通信・全体ビルド・実機未検証。実プロジェクト変更なし。'}
(b/'simpler_proposal.json').write_text(json.dumps({'request':req,'completion':comp,'report':report},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
