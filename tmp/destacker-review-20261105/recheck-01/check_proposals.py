"""再確認と提案の条件検算。実プロジェクトへの書込みは行わない。"""
from pathlib import Path
from collections import defaultdict
import json,re,copy
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'));s={x['name']:x['rows'] for x in d['sections']}
src=(b.parent.parent/'box-cycle-implement-20261105/check_conditions.py').read_text(encoding='utf-8')
ns={'defaultdict':defaultdict,'re':re};exec(src[src.index('class Model:'):src.index('\nresults=[]')],ns);Model=ns['Model']
dest=s['Destacker_段バラシ'];M=lambda n:f'Destacker_M[{n}]';checks=[]
def note(case,result):checks.append({'case':case,'result':result})
a=Model({M(9):True,'Out_CYw_Sep_Claw_F_Done':True,'HMI_RCON2_1_OUT_TargetPos[1]':100,'RCON2_1_OUT_TargetPos_mm':123})
a.row(dest[7]);assert a.env['RCON2_1_OUT_TargetPos_mm']==100;note('7行目の安全位置転送','修正を確認')
a=Model({'Destacker_End':True,'TimerQ_In_Sen_Supply_Container_Exist':False,'TimerQ_In_SenCY_Empty_Container_CY_H':True});a.row(dest[9]);assert a.env[M(12)];note('9行目のX1010 ONで通常入口成立','修正を確認')
a=Model({M(14):True,M(15):True,M(16):False});a.row(dest[11]);assert a.env[M(14)];a.env[M(16)]=True;a.row(dest[11]);assert not a.env[M(14)];note('11行目M14の保持は移動工程M16で解除','変更を確認')
a=Model({M(14):True,M(15):False});a.row(dest[12]);assert a.env[M(16)];note('12行目は確認OKなしでも移動要求','未対策')
a=Model({M(10):True,'RCON2_1_MoveDone':False});a.row(dest[8]);assert a.env[M(11)];note('8行目の軸完了待ち','未対策')
a=Model({M(7):True,'RCON2_1_MoveDone':True});a.row(dest[5]);a.row(dest[6]);assert a.env[M(9)];note('5→6行で旧完了を流用','未対策')
a=Model({'Auto_Com_Start':True,'TimerQ_In_Sen_Supply_Container_Exist':False,M(17):True});a.row(dest[0]);a.row(dest[1]);assert a.env[M(2)];note('通常工程中の初回再進入','未対策')
a=Model({M(13):True,'TimerQ_In_SenCY_Empty_Container_CY_H':True,'TimerQ_In_Sen_Container_Direction_Check':True,'TimerQ_In_Sen_Destacker_Stage_01_Exist':True});a.row(dest[11]);assert a.env[M(14)] and not a.env[M(15)];note('11行目の確認OKがX1010 OFFを要求','未対策')

#提案：確認中と確認OKを使い分ける。元の配線は保持し、検算用コピーだけ置換。
p=copy.deepcopy(dest[12]);p['CLs'][0]['Var']=M(15)
for ok in [False,True]:
    a=Model({M(14):True,M(15):ok});a.row(p);assert a.env[M(16)]==ok
note('提案：12行目開始をM15に変更','OKの2通りで期待一致')

# 11行目の提案コピー：共通戻り端、正しいDone、確認/異常のX1010をON条件へ。
confirm=copy.deepcopy(dest[11])
for c in confirm['CLs']:
    if c.get('X',0)>=5:c['X']=c.get('X',0)+1
    if c.get('Var')=='Out_CYw_Sep_Claw_H_Done':c['Var']='Out_CYw_Empty_Container_CY_H_Done'
    if c.get('Var')=='TimerQ_In_SenCY_Empty_Container_CY_H':c.pop('Not',None)
for v in confirm['VLs']:
    if v.get('X',0)>=5:v['X']+=1
confirm['CLs'].append({'__type':'LD','Var':'TimerQ_In_SenCY_Empty_Container_CY_H','X':5,'Y':0})
for mask in range(16):
    home,supply,direction,stage=[bool(mask&(1<<bit)) for bit in range(4)]
    a=Model({M(13):True,'TimerQ_In_SenCY_Empty_Container_CY_H':home,'TimerQ_In_Sen_Supply_Container_Exist':supply,'TimerQ_In_Sen_Container_Direction_Check':direction,'TimerQ_In_Sen_Destacker_Stage_01_Exist':stage})
    a.row(confirm);a.row(p)
    expected=home and not supply and direction and stage
    assert a.env[M(15)]==expected and a.env[M(16)]==expected,(mask,dict(a.env))
note('提案：11→12行の共通戻り端と確認OK','4入力の全16組でOKと移動要求が期待一致')
(b/'proposal_confirmation.json').write_text(json.dumps(confirm,ensure_ascii=False,indent=2),encoding='utf-8')

#提案：段ごとのDone OFF記憶。既存ステップと対応した6個の補助ビット。
guards=[(7,27,5),(8,28,6),(10,29,8),(16,30,13),(21,31,16),(23,32,18)]
for step,guard,target in guards:
    active=False;seen=False
    seq=[(False,True),(True,True),(True,False),(True,False),(True,True),(False,True)]
    out=[]
    for active,done in seq:
        seen=active and ((not done) or seen)
        out.append(active and seen and done)
    assert out==[False,False,False,False,True,False]
    assert M(guard) not in json.dumps(d['sections'],ensure_ascii=False)
note('提案：6移動の旧Done除外','各6状態、計36例で期待一致')
assert M(26) not in json.dumps(d['sections'],ensure_ascii=False)
assert 'Destacker_Init_Busy' not in json.dumps(d,ensure_ascii=False)
#提案：Busyは開始枝だけを遮断し、M1自己保持を切らない。完了は通常入口の受渡しで記憶。
busy=False;initial_done=False;m1=False;m2=False
m1=((True and not busy) or m1) and not m2 and not initial_done
busy=(m1 or busy) and not initial_done
assert m1 and busy
for _ in range(3):
    m1=((True and not busy) or m1) and not m2 and not initial_done
    busy=(m1 or busy) and not initial_done
    assert m1 and busy
m2=True;m1=((True and not busy) or m1) and not m2 and not initial_done
assert not m1
m2=False
for _ in range(3):
    m1=((True and not busy) or m1) and not m2 and not initial_done
    assert not m1 and busy
initial_done=True
busy=(m1 or busy) and not initial_done
for _ in range(3):
    m1=((True and not busy) or m1) and not m2 and not initial_done
    assert not m1 and not busy
note('提案：初回BusyとM26完了保持','初回待ち保持・初動中再開始禁止・完了後再開始禁止で期待一致')

#提案：既存RCON2_2受け側と同じNC Done→TON→Up、PEND OFF記憶を軸1へ。
receiver=[copy.deepcopy(s['RCON_IAI'][i]) for i in [322,323,324]]
for row in receiver:
    text=json.dumps(row,ensure_ascii=False).replace('RCON2_2_','RCON2_1_')
    row.clear();row.update(json.loads(text))
# 現存の3要求を6要求へ拡張する。配線は縦枝として追加。
r=receiver[0]
for c in r['CLs']:
    if c.get('Y')==3:c['Y']=6
for n in [4,5,6]:
    r['CLs'].append({'__type':'LD','Var':f'RCON2_1_Auto[{n}]','X':0,'Y':n-1})
    r['VLs'].append({'X':1,'Y':n-2,'Ix':100+n})
# 元自己保持枝の全セルをY6へ移したため、合流縦線も延長する。
for y in [3,4,5]:r['VLs'].append({'X':6,'Y':y,'Ix':200+y})

# モデル上の許可M3は外部入力。実通信・運転許可を生成したことにはしない。
a=Model({'RCON2_1_Ready':True,'RCON2_1_M[3]':True,'RCON2_1_Auto[1]':True,'RCON2_1_IN_PositionDone':True})
starts=[];dones=[];pend_off_at=None;pend_on_at=None;prev=False;switched=False
for tick in range(120):
    if tick==pend_off_at:a.env['RCON2_1_IN_PositionDone']=False
    if tick==pend_on_at:a.env['RCON2_1_IN_PositionDone']=True
    for row in receiver:a.row(row)
    now=a.env['RCON2_1_M[1]']
    if now and not prev:
        starts.append(tick);pend_off_at=tick+2;pend_on_at=tick+8
    prev=now
    if a.env['RCON2_1_MoveDone'] and (not dones or tick>dones[-1]+12):dones.append(tick)
    if a.env['RCON2_1_MoveDone'] and not switched:
        a.env['RCON2_1_Auto[1]']=False;a.env['RCON2_1_Auto[2]']=True;switched=True
    elif len(dones)>=2:
        a.env['RCON2_1_Auto[2]']=False
assert len(starts)==2 and len(dones)==2,(starts,dones)
assert starts[0]>=9 and starts[1]>dones[0]+10,(starts,dones)
note('提案：要求ORが切れない2連続移動','受付2回・新しいPEND OFF→ON後の完了2回')
a=Model({'RCON2_1_Ready':True,'RCON2_1_M[3]':True,'RCON2_1_Auto[1]':True,'RCON2_1_IN_PositionDone':True})
for _ in range(30):
    for row in receiver:a.row(row)
assert not a.env['RCON2_1_MoveDone'];note('提案：PENDが最初からONのまま','完了を誤生成しない')

(b/'proposal_receiver.json').write_text(json.dumps(receiver,ensure_ascii=False,indent=2),encoding='utf-8')
o={'checks':checks,'guards':[{'step':x,'guard':y,'transition_row':z} for x,y,z in guards],'receiver_model':{'starts':starts,'dones':dones,'dt_ms':10},'scope':'保存配線の静的条件と提案の限定モデル。実プロジェクト未変更。Start実出力・通信・実機・全工程モデルではない。'}
(b/'checks.json').write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(o,ensure_ascii=False))
