"""主工程とRCON内部受付を接続した仮想応答モデル。実出力禁止は解除しない。"""
from pathlib import Path
from collections import defaultdict
import json,re,sys
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;m=json.loads((b/'build.json').read_text(encoding='utf-8'));p=sm.Project(m['stage']);rows=p.section('ST7_A_Dis2_左SF排出')['rows'];rs=p.section('RCON_IAI')['rows'];rm={int(k):v for k,v in m['rcon_old_to_new_rows'].items()}
src=Path('C:/Users/SEIGI-N13/work-projects/tmp/st7-dis2-review-20261106/check.py').read_text(encoding='utf-8');ns={'defaultdict':defaultdict,'re':re};exec(src[src.index('class Model:'):src.index('\nchecks=[]')],ns);Model=ns['Model']
items=[0]+[1]*5+[4,5]+[1]*5+[0,1]
def test(axis_delay,cylinder_delay,pulse_len):
    e={'Auto_A_Start':True,'AutoMode':True,'P_On':True,'P_Off':False,'A_SF_CT':0,'HMI_A_SF_StackPitch_mm':-10.,'RCON1_5_SafePos_mm':10.,'RCON1_3_Ready':True,'RCON1_5_Ready':True,'RCON1_3_IN_PositionDone':True,'RCON1_5_IN_PositionDone':True,'TimerQ_In_SenCY_SH_A_Turn_H':True}
    for axis in [3,5]:
        for n in range(1,9):e[f'HMI_RCON1_{axis}_OUT_TargetPos[{n}]']={1:0.,2:100.,3:200.,4:210.,5:220.,6:230.,7:250.,8:300.}[n]
    a=Model(e);env=a.e;idx=0;events=[];prev={};trace=[];placed=[];rotations=[];next_tick=None;clear_tick=None;pickup_at=None;finished=[];rack=0
    def load_item(code):
        env['Station_A_Data[7].Work_On']=bool(code);env['TimerQ_In_Sen_Work_A_Pos_07']=bool(code)
        env['Station_A_Data[7].Total_Judge']=1 if code==1 else 9 if code else 0
        env['Station_A_Data[7].Judgment_Details']=code if code in [4,5] else 0
    load_item(items[0])
    cyls=sorted({c['Var'] for r in rows for c in r['CLs'] if c['__type']=='ST' and c.get('Var','').startswith('Out_CYw_') and '_Auto[' in c.get('Var','')})
    for tick in range(12000):
        if clear_tick==tick:env['Ins_A_Next_Cycle']=False;clear_tick=None
        if next_tick==tick:
            idx+=1;load_item(items[idx]);env['Ins_A_Next_Cycle']=True;clear_tick=tick+1;next_tick=None
        if pickup_at==tick:
            env['BoxPacking_A_Pickup_Done']=True;env['TimerQ_In_Sen_SH_A_Ext']=False;events.append((tick+2,'value','BoxPacking_A_Pickup_Done',False));pickup_at=None
        for ev in events[:]:
            at,kind,key,val=ev
            if at!=tick:continue
            events.remove(ev)
            if kind=='value':env[key]=val
            elif kind=='axis':env[f'RCON1_{key}_ActualPos_mm']=val
            elif kind=='release':
                placed.append((idx,items[idx],val));trace.append([tick,'配置完了',idx,items[idx],val])
                if items[idx]==1:
                    rack+=1
                    if rack==5:env['TimerQ_In_Sen_SH_A_Ent']=True
            elif kind=='turn':
                env['TimerQ_In_Sen_SH_A_Ent']=False;env['TimerQ_In_Sen_SH_A_Ext']=True;rack=0
                env['TimerQ_In_SenCY_SH_A_Turn_H']=key=='H';env['TimerQ_In_SenCY_SH_A_Turn_F']=key=='F';rotations.append(tick);trace.append([tick,'回転完了',idx])
        for n,r in enumerate(rows):a.row(r,'main'+str(n))
        phases=[n for n in range(1,46) if env[f'ST7_A_Dis2_M[{n}]']]
        if phases!=prev.get('phases'):trace.append([tick,'工程状態',idx,env['A_SF_CT'],phases]);prev['phases']=phases
        for axis,start,finish in [(3,120,121),(5,201,202)]:
            for i in [rm[start],rm[finish]-1,rm[finish]]:a.row(rs[i],'rcon'+str(i))
            key=f'RCON1_{axis}_M[1]';active=bool(env[key]);old=prev.get(key,False);prev[key]=active
            if active and not old:
                target=env[f'RCON1_{axis}_OUT_TargetPos_mm'];pend=f'RCON1_{axis}_IN_PositionDone'
                events.extend([(tick+2,'value',pend,False),(tick+axis_delay,'value',pend,True),(tick+axis_delay,'axis',axis,target)])
                trace.append([tick,'軸の内部受付',axis,target])
        for command in cyls:
            active=bool(env[command]);old=prev.get(command,False);prev[command]=active
            if not active or old:continue
            done=re.sub(r'_Auto\[\d+\]$','_Done',command)
            events.extend([(tick+cylinder_delay,'value',done,True),(tick+cylinder_delay+pulse_len,'value',done,False)])
            trace.append([tick,'シリンダ要求',command])
            if command=='Out_CYw_Ejc_Hldr_Feed_A_F_Auto[1]':assert items[idx]==1,('NGで送り行',idx)
            if command=='Out_CYw_Disc_Chk_A_H_Auto[2]':
                target=env['RCON1_5_OUT_TargetPos_mm'];events.append((tick+cylinder_delay,'release','',target))
            if command.startswith('Out_CYw_SH_A_Turn_'):
                assert env['TimerQ_In_Sen_SH_A_Ent'] and not env['TimerQ_In_Sen_SH_A_Ext']
                events.append((tick+cylinder_delay,'turn','H' if '_H_' in command else 'F',True))
        waiting=bool(env['ST7_A_SF_Wait_Pickup'])
        if waiting and not prev.get('wait',False):pickup_at=tick+20
        prev['wait']=waiting
        complete=bool(env['ST7_A_Dis2_End'])
        if complete and not prev.get('end',False):
            finished.append(idx);trace.append([tick,'ST7完了',idx,items[idx],env['A_SF_CT']])
            if idx<len(items)-1:next_tick=tick+4
        prev['end']=complete
        if env['ST7_A_Dis2_M[43]'] or env['ST7_A_Dis2_M[44]']:
            (b/'failed_flow.json').write_text(json.dumps({'tick':tick,'index':idx,'trace':trace,'env':dict(env)},ensure_ascii=False,indent=2),encoding='utf-8');raise AssertionError(('工程異常',idx,tick))
        if len(finished)==len(items) and len(rotations)>=2:
            codes=[c for _,c,_ in placed];assert codes==[x for x in items if x],codes
            positions=[v for _,c,v in placed if c==1];assert positions==[200.,190.,180.,170.,160.]*2+[200.],positions
            assert [v for _,c,v in placed if c in [4,5]]==[250.,300.]
            return {'axis_response_scans':axis_delay,'cylinder_response_scans':cylinder_delay,'cylinder_done_hold_scans':pulse_len,'scans':tick+1,'completed_items':len(finished),'placed_items':len(placed),'rotations':len(rotations),'OK_positions':positions,'trace':trace}
    (b/'failed_flow.json').write_text(json.dumps({'index':idx,'trace':trace,'env':dict(env),'pending':events},ensure_ascii=False,indent=2),encoding='utf-8');raise AssertionError(('工程停止',idx,trace[-10:]))
runs=[]
for ad,cd,pl in [(6,2,1),(10,3,1),(8,2,5),(15,5,8)]:runs.append(test(ad,cd,pl))
sm.save_json(b/'flow.json',{'candidate_sha':p.fingerprint,'runs':runs,'scope':f'主工程{len(rows)}行と対象2軸の内部受付・今回完了を接続。シリンダDone/PEND/センサーは仮想外部応答。実出力P_Offは解除せず、実通信/Output全体との機械結合は未検証。10msはモデル刻み。'})
print(json.dumps({'runs':len(runs),'items_per_run':len(items),'OK_positions':runs[0]['OK_positions'],'passed':True},ensure_ascii=False))
