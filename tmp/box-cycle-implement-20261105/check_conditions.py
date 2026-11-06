"""生成ラダーの制御条件モデル。メーカーPLCシミュレーター・実機ではない。"""
from pathlib import Path
from zipfile import ZipFile
from collections import defaultdict
from itertools import product
import json,re
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
with ZipFile(m['staged']) as z:
    box=[json.loads(l) for l in z.read(m['box_part']).decode('utf-8-sig').splitlines()]
    sf=[json.loads(l) for l in z.read(m['sf_part']).decode('utf-8-sig').splitlines()]
mp={int(k):v for k,v in m['old_to_new_rows'].items()}
M=lambda n:f'BoxPacking_M[{n}]'

class Model:
    def __init__(self,env=None):self.env=defaultdict(lambda:False,env or {});self.up={};self.fb={};self.dt=10
    def value(self,var):
        if '#' in var:
            kind,num=var.split('#',1)
            if kind in ['INT','UINT','DINT','LREAL','REAL']:return float(num) if '.' in num else int(num)
        return self.env[var]
    def row(self,r):
        edges=defaultdict(set);functions=[];blocks=[];seen=set();todo=[]
        for v in r['VLs']:
            p=(v.get('X',0),v.get('Y',0));q=(p[0],p[1]+1)
            edges[p].add(q);edges[q].add(p)
        for c in r['CLs']:
            kind=c['__type'];allow=False
            if kind=='HL':allow=True
            elif kind=='LD':allow=bool(self.value(c['Var']))!=c.get('Not',False)
            elif kind=='F':
                name=c['Name'];args=[self.value(p['Var']) for p in c.get('In',[]) if p['__type']=='PRM']
                if name=='=':allow=args[0]==args[1]
                elif name=='<>':allow=args[0]!=args[1]
                elif name=='<':allow=args[0]<args[1]
                elif name=='>':allow=args[0]>args[1]
                elif name=='>=':allow=args[0]>=args[1]
                elif name=='Up':allow=not self.up.get(c['Id'],False)
                else:allow=True
                functions.append(c)
            elif kind=='FB':blocks.append(c)
            elif kind=='IST':allow=True # XY計算本文は不変。数値計算は今回のモデル対象外。
            if allow:edges[(c.get('X',0),c.get('Y',0))].add((c.get('X',0)+1,c.get('Y',0)))
        seen={(0,y) for y in range(max(c.get('Y',0) for c in r['CLs'])+1)};todo=list(seen)
        while todo:
            for p in edges[todo.pop()]-seen:seen.add(p);todo.append(p)
        # 既存のTON/TOFを10ms刻みの条件モデルとして扱う。
        for c in sorted(blocks,key=lambda c:c.get('X',0)):
            active=(c.get('X',0),c.get('Y',0)) in seen
            pt=next(p['Var'] for p in c['In'] if p.get('Arg')=='PT')
            match=re.fullmatch(r'T#(\d+)(ms|s)',pt);assert match,pt
            duration=int(match[1])*(1000 if match[2]=='s' else 1)
            prior=self.fb.get(c['Var'],0)
            if c['Name']=='TON':state=min(duration,prior+self.dt) if active else 0;q=state>=duration
            elif c['Name']=='TOF':state=duration if active else max(0,prior-self.dt);q=active or state>0
            else:raise AssertionError(c['Name'])
            self.fb[c['Var']]=state;self.env[c['Var']+'.Q']=q
            if q:
                p=(c.get('X',0)+1,c.get('Y',0));todo=[]
                if active or c['Name']=='TOF':
                    if p not in seen:seen.add(p);todo.append(p)
                while todo:
                    for p in edges[todo.pop()]-seen:seen.add(p);todo.append(p)
        for c in sorted(functions,key=lambda c:c.get('X',0)):
            active=(c.get('X',0),c.get('Y',0)) in seen
            if c['Name']=='Up':self.up[c['Id']]=active
            elif active and c['Name'] in ['+','MOVE']:
                args=[self.value(p['Var']) for p in c.get('In',[]) if p['__type']=='PRM']
                out=[p['Var'] for p in c['Out'] if p['__type']=='PRM']
                self.env[out[0]]=args[0]+args[1] if c['Name']=='+' else args[0]
        for c in r['CLs']:
            if c['__type']=='ST':self.env[c['Var']]=(c.get('X',0),c.get('Y',0)) in seen

results=[]
# ST7の3枝に対する解除が全組合せで優先されること。
for start1,start2,held,ack in product([False,True],repeat=4):
    sim=Model({'ST7_A_SF_M[3]':start1,'Out_CYw_SH_A_Turn_H_Done':True,
        'ST7_A_SF_M[4]':start2,'Out_CYw_SH_A_Turn_F_Done':True,
        'ST7_A_SF_Wait_Pickup':held,'BoxPacking_A_Pickup_Done':ack})
    sim.row(sf[31]);assert sim.env['ST7_A_SF_Wait_Pickup']==((start1 or start2 or held) and not ack)
results.append({'test':'ST7 A待ちの生成・自己保持・共通解除','cases':16})

# 物理的な完了前のBusyだけでは待ちを解除しない。
for busy,phase,done in product([False,True],repeat=3):
    sim=Model({'BoxPacking_A_Busy':busy,M(34):phase,'RCON2_4_MoveDone':done})
    sim.row(box[30]);assert sim.env['BoxPacking_A_Pickup_Done']==(busy and phase and done)
results.append({'test':'A取出し完了の3条件','cases':8})

# Z上昇完了がOFFの間は、配置後の入数判定へ進めない。
for count in [5,75,80]:
    sim=Model({M(42):True,'RCON2_4_MoveDone':False,'Box_Total_CT':count})
    sim.row(box[mp[36]]);assert not sim.env[M(43)] and not sim.env[M(44)] and not sim.env[M(45)]
    sim.env['RCON2_4_MoveDone']=True;sim.row(box[mp[36]])
    assert sim.env[M(43)] and sim.env[M(44)]==(count<80) and sim.env[M(45)]==(count==80)
results.append({'test':'配置後Z上昇完了ONでのみ継続・満杯判定','cases':6})

# 満杯排出後の軸戻り完了でリセット。完了自己保持中には再リセットしない。
sim=Model({M(49):True,'Box_Total_CT':80,'RCON2_5_MoveDone':False})
sim.row(box[mp[41]]);assert sim.env['Box_Total_CT']==80 and not sim.env['BoxPacking_End']
sim.env['RCON2_5_MoveDone']=True;sim.row(box[mp[41]])
assert sim.env['Box_Total_CT']==0 and sim.env['BoxPacking_End']
sim.env['Box_Total_CT']=5;sim.row(box[mp[41]]);assert sim.env['Box_Total_CT']==5
results.append({'test':'排出後戻り完了の立上り1回リセット','cases':3})

def run_machine(delay,preparation,initial_pos,held_done=False):
    env={'Auto_Com_Start':True,'TimerQ_In_Sen_Tray_Direction_Check':True,'Box_Total_CT':0,
        'RCON2_5_ActualPos_mm':initial_pos,'ST7_A_SF_M[3]':True,'Out_CYw_SH_A_Turn_H_Done':True,
        'TimerQ_In_Sen_Container_Arrival':initial_pos==0}
    for axis in [2,3,4,5]:
        for n in [1,2,3]:env[f'HMI_RCON2_{axis}_OUT_TargetPos[{n}]']=(n-1)*100
    model=Model(env);e=model.env;pending=[];pulse_until={};previous={};events=[];counts=[];full=[];next_ready=None;was_wait=False;init_seen=False
    commands=[(c['Var'],f'RCON2_{c["Var"].split("_")[1]}_MoveDone') for r in box for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'RCON2_[2-5]_Auto\[\d+\]',c.get('Var',''))]
    commands += [(c['Var'],re.sub(r'_Auto\[\d+\]$','_Done',c['Var'])) for r in box for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'Out_CYw_.*_Auto\[\d+\]',c.get('Var',''))]
    for tick in range(3500):
        for signal,end in list(pulse_until.items()):
            if tick>=end:e[signal]=False;del pulse_until[signal]
        for at,signal,axis,pos in list(pending):
            if at!=tick:continue
            pending.remove((at,signal,axis,pos));e[signal]=True
            pulse_until[signal]=tick+(10 if axis else 100) if held_done else tick+1
            if axis==5:
                e['RCON2_5_ActualPos_mm']=pos
                if pos==100:e['TimerQ_In_Sen_Container_Arrival']=False
        if next_ready is not None and tick>=next_ready:
            e['ST7_A_SF_M[3]']=True;e['Out_CYw_SH_A_Turn_H_Done']=True;next_ready=None
        before=dict(e)
        # ST7とBoxは同一POU。現保存順と同じST7→Boxで受渡しを検査する。
        model.row(sf[31])
        if e['ST7_A_SF_Wait_Pickup']:
            e['ST7_A_SF_M[3]']=False;e['Out_CYw_SH_A_Turn_H_Done']=False
        if was_wait and not e['ST7_A_SF_Wait_Pickup']:next_ready=tick+max(1,preparation)
        was_wait=e['ST7_A_SF_Wait_Pickup']
        for r in box:model.row(r)
        if e[M(2)]:init_seen=True
        if init_seen:assert not e[M(1)] and not e[M(3)],('初回再進入',tick)
        if e['BoxPacking_A_Busy'] and not before.get('BoxPacking_A_Busy'):
            counts.append(e['Box_Total_CT']);events.append([tick,'A取出し開始',e['Box_Total_CT']])
        if e['BoxPacking_A_Pickup_Done'] and not before.get('BoxPacking_A_Pickup_Done'):
            events.append([tick,'A取出しZ退避完了',e['Box_Total_CT']])
        if e['BoxPacking_End'] and not before.get('BoxPacking_End'):
            assert e['Box_Total_CT']==0
            full.append(tick);events.append([tick,'満杯排出・軸戻り完了',0])
        for command,signal in commands:
            active=bool(e[command]);prior=previous.get(command,False);previous[command]=active
            if active and not prior:
                ax=int(command.split('_')[1]) if command.startswith('RCON2_') else None
                pos=e[f'RCON2_{ax}_OUT_TargetPos_mm'] if ax else None
                pending.append((tick+delay,signal,ax,pos))
                if command.startswith('Out_CYw_Ejc_Cont_F_Auto'):
                    pending.append((tick+delay,'TimerQ_In_Sen_Container_Pass',None,None))
        # 次の空コンテナは受渡位置で到着する。設置位置ではX1003はOFF。
        if e['RCON2_5_ActualPos_mm']==0 and (full or previous.get('RCON2_5_Auto[3]',False)):
            e['TimerQ_In_Sen_Container_Arrival']=True
        if len(full)>=2 and len(counts)>=33:
            assert counts==list(range(5,81,5))*2+[5],counts
            return {'delay_scans':delay,'preparation_scans':preparation,'initial_position':initial_pos,'held_done_100ms_1s':held_done,'scans':tick+1,'pickup_counts':counts,'completed_boxes':2,'initial_repeat':False,'events':events}
    (b/'failed_trace.json').write_text(json.dumps({'events':events,'env':dict(e),'pending':pending},ensure_ascii=False,indent=2),encoding='utf-8')
    raise AssertionError(('モデル停止',delay,preparation,initial_pos,tick,events[-8:]))

machines=[]
for delay,prep,pos in product([2,4],[1,10,50],[0,100,150,200]):
    machines.append(run_machine(delay,prep,pos))
for delay,prep,pos in product([2,4],[1,50],[0,100]):
    machines.append(run_machine(delay,prep,pos,True))
results.append({'test':'A側で2箱連続80個＋次箱5個までの条件モデル','cases':len(machines),'pickup_events_per_case':33,'initial_positions':['受渡位置','設置位置（X1003 OFF）','位置未確定','排出位置'],'actuator_completion':'遅延後の完了入力を外部供給。RCON受け側・実機動作を模擬していない'})
out={'results':results,'machines':machines,'scope':'Box全45行とST7待ち31行の条件モデル。ST7の製造工程・異常TON・XYの不変ST本文・RCON通信・PLC全体シミュレーション・実機は対象外。'}
(b/'conditions.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'results':results,'machine_runs':len(machines)},ensure_ascii=False))
