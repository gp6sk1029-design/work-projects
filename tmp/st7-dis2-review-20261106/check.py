"""保存ラダーの結線を使った局所反例検算。PLCシミュレータではない。"""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import product
import json,re,copy,sys
b=Path(__file__).parent;d=json.loads((b/'snapshot.json').read_text(encoding='utf-8'))
s={x['name']:x['rows'] for x in d['sections']};rows=s['ST7_A_Dis2_左SF排出'];M=lambda n:f'ST7_A_Dis2_M[{n}]'
class Model:
    def __init__(self,values=None):self.e=defaultdict(lambda:False,values or {});self.prev={};self.times={};self.log=[]
    def value(self,v):
        if v in ['TRUE','FALSE']:return v=='TRUE'
        if '#' in v and not v.startswith('T#'):
            kind,v=v.split('#',1)
            if kind in ['INT','UINT','REAL','LREAL','DINT','UDINT']:return float(v)
        if re.fullmatch(r'[-+]?\d+(\.\d+)?',v):return float(v)
        return self.e[v]
    def row(self,r,rid=''):
        cs=r['CLs'];maxy=max([c.get('Y',0) for c in cs]+[v.get('Y',0)+1 for v in r['VLs']]);energized={(0,y) for y in range(maxy+1)}
        for x in range(max(c.get('X',0) for c in cs)+1):
            changed=True
            while changed:
                changed=False
                for v in r['VLs']:
                    if v.get('X',0)!=x:continue
                    a=(x,v.get('Y',0));c=(x,v.get('Y',0)+1)
                    if (a in energized)!=(c in energized):energized.update([a,c]);changed=True
            for c in sorted([c for c in cs if c.get('X',0)==x],key=lambda c:c.get('Y',0)):
                y=c.get('Y',0);power=(x,y) in energized;kind=c['__type'];out=False
                if kind=='HL':out=power
                elif kind=='LD':
                    val=bool(self.value(c['Var']));out=power and (not val if c.get('Not') else val)
                    assert not c.get('Up'), '今回のモデル対象外：微分接点'
                elif kind=='ST':
                    if c.get('S'):
                        if power:self.e[c['Var']]=True
                    elif c.get('RS'):
                        if power:self.e[c['Var']]=False
                    else:self.e[c['Var']]=power
                    self.log.append((rid,c['Var'],self.e[c['Var']]))
                elif kind=='F':
                    name=c['Name'];args=[self.value(z['Var']) for z in c.get('In',[]) if z.get('__type')=='PRM' and z.get('Var')]
                    dst=[z['Var'] for z in c.get('Out',[]) if z.get('__type')=='PRM' and z.get('Var')]
                    if name=='Up':
                        key=c.get('Id',str((rid,x,y)));out=power and not self.prev.get(key,False);self.prev[key]=power
                    elif name in ['=','<>','<','>','<=','>=']:
                        a,z=args;out=power and {'=':a==z,'<>':a!=z,'<':a<z,'>':a>z,'<=':a<=z,'>=':a>=z}[name]
                    elif name in ['MOVE','+','-','*']:
                        out=power
                        if power:self.e[dst[0]]=args[0] if name=='MOVE' else (args[0]+args[1] if name=='+' else args[0]-args[1] if name=='-' else args[0]*args[1])
                    else:raise AssertionError(name)
                elif kind=='FB':
                    assert c['Name']=='TON';pt=next(z['Var'] for z in c['In'] if z.get('Arg')=='PT');mat=re.fullmatch(r'T#([\d.]+)(ms|s)',pt);assert mat
                    dur=float(mat[1])*(1000 if mat[2]=='s' else 1);key=c['Var'];self.times[key]=self.times.get(key,0)+10 if power else 0
                    out=power and self.times[key]>=dur;self.e[key+'.Q']=out
                else:raise AssertionError(kind)
                if out:energized.add((x+1,y))
        return self.e
checks=[]
def record(name,values):checks.append({'name':name,'evidence':values})
# 同じ要求を通常コイルで2回書くため、後段OFFが先行ONを打ち消す。
a=Model({M(12):True});a.row(rows[10],10);first=a.e['RCON1_5_Auto[2]'];a.row(rows[19],19);last=a.e['RCON1_5_Auto[2]'];assert first and not last
record('10→19行：回収下降要求がON→OFFに上書き',{'after_10':first,'after_19':last})
# 完了時の戻要求[3]はOutputの動作/監視双方にない。
req='Out_CYw_Ejc_Hldr_Feed_A_H_Auto[3]';receivers=[]
for name,rs in s.items():
    for n,r in enumerate(rs):
        if any(c.get('Var')==req and c['__type']=='LD' for c in r['CLs']):receivers.append([name,n])
assert receivers==[];record('25行：送り戻要求[3]の受け接点0',{'request':req,'contacts':receivers,'output_rows':[106,108]})
# ワークなしはM10まで立つが、保持したままEndへ行けない。
a=Model({M(8):True,'Station_A_Data[7].Work_On':False,'TimerQ_In_Sen_Work_A_Pos_07':False})
for tick in range(8):
    for n in range(8,27):a.row(rows[n],n)
assert a.e[M(10)] and not a.e['ST7_A_Dis2_End']
record('8行：ワークなし経路で8走査保持しても完了しない',{'M8':a.e[M(8)],'M10':a.e[M(10)],'End':a.e['ST7_A_Dis2_End']})
# End保持はNextCycleでも解除されない。次回M33にも進めない。
a=Model({'ST7_A_Dis2_End':True,'Ins_A_Next_Cycle':True});a.row(rows[26],26);assert a.e['ST7_A_Dis2_End']
a.e[M(32)]=True;a.e['RCON1_3_MoveDone']=True;a.row(rows[25],25);assert not a.e[M(33)]
record('26行：NextCycleでEndが残る、25行M33を阻害',{'End':a.e['ST7_A_Dis2_End'],'M33':a.e[M(33)]})
# A満杯／B空で正常枝と異常枝が同時にON。B満杯だけで正常枝が消える。
full_cases=[]
for fa,fb in product([False,True],repeat=2):
    a=Model({M(8):True,'Station_A_Data[7].Work_On':True,'TimerQ_In_Sen_Work_A_Pos_07':True,'TimerQ_In_Sen_NG2_Tray_A_Full':fa,'TimerQ_In_Sen_NG2_Tray_B_Full':fb})
    a.row(rows[8],8);full_cases.append({'A_full':fa,'B_full':fb,'M9':a.e[M(9)],'M11':a.e[M(11)]})
assert full_cases[2]['M9'] and full_cases[2]['M11'];assert not full_cases[1]['M9'] and not full_cases[1]['M11']
record('8行：A/B満杯の参照不一致4組',full_cases)
# NG枝は送り完了を迂回。NG1/NG2とも横移動が出る。
branch=[]
for choice in [18,19,20]:
    a=Model({M(17):True,M(choice):True,'Out_CYw_Ejc_Hldr_Feed_A_F_Done':False});a.row(rows[16],16)
    branch.append({'choice':choice,'feed_done':False,'move':a.e[M(22)]})
assert [x['move'] for x in branch]==[False,True,True];record('16行：NG枝だけ送り完了を待たない',branch)
# 旧DoneがONなら、新しい要求が立った同じ走査で次工程へ行ける。
a=Model({M(15):True,'RCON1_5_MoveDone':True,'Station_A_Data[7].Total_Judge':1,'A_SF_CT':0});a.row(rows[13],13);a.row(rows[14],14)
assert a.e[M(17)] and a.e['A_SF_CT']==1;record('13→14行：旧Done ONで仕分けへ即通過',{'M16':a.e[M(16)],'M17':a.e[M(17)],'count':a.e['A_SF_CT']})
# 回転の入口に積数条件なし。A/B条件を比較。
turn=[]
for count,ae,be in [(1,True,False),(1,False,True),(5,True,False),(5,False,True)]:
    a=Model({'Auto_A_Start':True,'A_SF_CT':count,'TimerQ_In_Sen_SH_A_Ent':ae,'TimerQ_In_Sen_SH_B_Ent':be,'RCON1_5_ActualPos_mm':0,'RCON1_5_SafePos_mm':10})
    a.row(rows[27],27);turn.append({'count':count,'A_ent':ae,'B_ent':be,'M1':a.e['ST7_A_SF_M[1]']})
assert turn[1]['M1'] and not turn[0]['M1'];record('27行：A回転をB側INで開始、積数1でも開始',turn)
# SF_BUSYだけ立ち、端位置未検出だと命令が出ず待ち続ける。
a=Model({'Auto_A_Start':True,'TimerQ_In_Sen_SH_B_Ent':True,'RCON1_5_ActualPos_mm':0,'RCON1_5_SafePos_mm':10})
for tick in range(4):
    for n in range(27,32):a.row(rows[n],n)
assert a.e['ST7_A_SF_Busy'] and not a.e['Out_CYw_SH_A_Turn_H_Auto[1]'] and not a.e['Out_CYw_SH_A_Turn_F_Auto[1]']
record('27～31行：ターン両端OFFでBusyだけ保持',{'Busy':a.e['ST7_A_SF_Busy'],'turn_H':a.e['Out_CYw_SH_A_Turn_H_Auto[1]'],'turn_F':a.e['Out_CYw_SH_A_Turn_F_Auto[1]']})
# 14行再入場でカウントが二重に増える。21行は5段完了を即0にする。
a=Model({M(16):True,'RCON1_5_MoveDone':True,'Station_A_Data[7].Total_Judge':1,'A_SF_CT':0});a.row(rows[14],14);assert a.e['A_SF_CT']==1
a.e['Retry[12]']=True;a.row(rows[14],14);a.e['Retry[12]']=False;a.row(rows[14],14);assert a.e['A_SF_CT']==2
record('14行：同一ワークでRetry後の再進入は再加算',{'count_after_retry':a.e['A_SF_CT']})
a=Model({M(28):True,'Out_CYw_Disc_Chk_A_H_Done':True,'Station_A_Data[7].Total_Judge':1,'A_SF_CT':5});a.row(rows[21],21);assert a.e['A_SF_CT']==0
record('21行：5個目解放後、回転前に積数0',{'A_SF_CT':a.e['A_SF_CT']})
# 計算式は1～5で正しいが、基準[3]と説明[2]が不一致。範囲外で新規MOVEをしない。
calc=[]
for count in [0,1,2,3,4,5,6]:
    a=Model({'A_SF_CT':count,'HMI_RCON1_5_OUT_TargetPos[3]':100,'HMI_RCON1_5_OUT_TargetPos[2]':200,'HMI_A_SF_StackPitch_mm':-10,M(22):True,'RCON1_3_MoveDone':True,'Station_A_Data[7].Total_Judge':1,'RCON1_5_OUT_TargetPos_mm':777})
    a.row(rows[17],17);a.row(rows[18],18)
    calc.append({'count':count,'calculated':a.e['A_SF_StackTarget_mm'],'transfer':a.e['RCON1_5_OUT_TargetPos_mm'],'ready':a.e[M(24)]})
assert [x['transfer'] for x in calc[1:6]]==[100,90,80,70,60];assert calc[0]['transfer']==calc[6]['transfer']==777
record('17～18行：基準[3]、範囲0/6は前目標保持',calc)
# 要求先・重複・物理転送P_Offを含む機械判定用一覧。
writers=defaultdict(list);contacts=defaultdict(list)
for name,rs in s.items():
    for n,r in enumerate(rs):
        for c in r['CLs']:
            if c['__type']=='ST':writers[c['Var']].append({'section':name,'row':n,'S':c.get('S',False),'RS':c.get('RS',False)})
            if c['__type']=='LD':contacts[c['Var']].append({'section':name,'row':n})
requests=sorted({c['Var'] for r in rows for c in r['CLs'] if c['__type']=='ST' and ('_Auto[' in c['Var'])})
audit={v:{'writers':writers[v],'contacts':contacts[v]} for v in requests}
sm_names=[s['RCON_IAI'][i] for i in [81,87,89,162,168,170]]
smout={'checks':checks,'request_audit':audit,'physical_transfer_rows':[{'row':i,'CMT':s['RCON_IAI'][i].get('CMT'),'rung':s['RCON_IAI'][i]} for i in [81,87,89,162,168,170]],'scope':'局所の結線・通常コイル書込み順・算術・状態保持の条件モデル。10msは仮刻み。実機、全体ビルド、通信は未検証。原本は変更しない。'}
(b/'checks.json').write_text(json.dumps(smout,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':checks,'requests':audit},ensure_ascii=False,indent=2))
