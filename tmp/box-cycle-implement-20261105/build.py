"""合意した初回・A取出し受渡し・次箱処理を、既存ラダーのまま限定修正する。"""
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy,copy
from lxml import etree as E
import json,io,re,hashlib,uuid

b=Path(__file__).parent
d=json.loads((b/'project.json').read_text(encoding='utf-8'))
src=Path(d['source']);raw=(b/'source.smc2').read_bytes()
assert src.read_bytes()==raw and hashlib.sha256(raw).hexdigest()==d['sha256']
sections={s['name']:s for s in d['sections']}
boxname='BoxPacking_箱詰め';sfname='ST7_A_Dis2_左SF排出'
box=deepcopy(sections[boxname]['rows']);sf=deepcopy(sections[sfname]['rows']);rcon=deepcopy(sections['RCON_IAI']['rows'])
assert len(box)==42 and len(sf)==32
dest=src.with_name(src.name.replace('20261105F.smc2','20261105G.smc2'))
assert dest!=src and not dest.exists()
mode=json.loads((b/'decisions.json').read_text(encoding='utf-8'))
assert mode['a_wait_reset']=='z_up_complete' and mode['count_reset']=='container_return_complete'
assert mode['initial_arrival'] in ['preserve','require_at_install']

def reindex(r):
    n=0
    for c in r['CLs']:
        if c['__type']!='HL':c['Ix']=n;n+=1
        for p in c.get('In',[])+c.get('Out',[]):
            if p['__type']=='PRM':p['Ix']=n;n+=1
    r['LRI']=n;r['RRI']=n+1;n+=2
    for v in r['VLs']:v['Ix']=n;n+=1
    return r

def ld(v,x=0,y=0,nc=False):
    r={'__type':'LD','Var':v}
    if x:r['X']=x
    if y:r['Y']=y
    if nc:r['Not']=True
    return r

def co(v,x=1,y=0):
    r={'__type':'ST','Var':v,'X':x}
    if y:r['Y']=y
    return r

def newrow(cs,vs=None,comment=''):
    return reindex({'CLs':cs,'VLs':vs or [],'CMT':comment})

def renumber(v):
    if isinstance(v,dict):
        for k,x in v.items():
            if k=='Var' and isinstance(x,str):
                m=re.fullmatch(r'BoxPacking_M\[(\d+)\]',x)
                if m:
                    n=int(m[1]);assert 1<=n<=48
                    if n>=2:v[k]=f'BoxPacking_M[{n+1}]'
            else:renumber(x)
    elif isinstance(v,list):
        for x in v:renumber(x)

renumber(box)

# 初回開始：開始枝だけにBusy/完了の否定接点を追加。M1自己保持は迂回。
r=box[0]
for c in r['CLs']:
    if c.get('X',0)>=1:c['X']+=2
for v in r['VLs']:
    if v.get('X',0)>=1:v['X']+=2
r['CLs'] += [ld('BoxPacking_Init_Busy',1,nc=True),ld('BoxPacking_M[2]',2,nc=True),{'__type':'HL','X':1,'Y':1},{'__type':'HL','X':2,'Y':1}]
reindex(r)

# 初回状態判定・分岐全体に初回完了の共通否定接点を追加。
r=box[1]
for c in r['CLs']:
    if c.get('X',0)>=6:c['X']+=1
for v in r['VLs']:
    if v.get('X',0)>=6:v['X']+=1
r['CLs'].append(ld('BoxPacking_M[2]',6,nc=True));reindex(r)

# 初回方向判定の自己保持も、取出し先へ受渡し後に解除する。
r=box[4]
for c in r['CLs']:
    if c.get('X',0)>=3:c['X']+=1
for v in r['VLs']:
    if v.get('X',0)>=3:v['X']+=1
r['CLs'].append(ld('BoxPacking_M[2]',3,nc=True));reindex(r)

# 到着確認の追加はセンサー検出範囲を確認した場合だけ実施する。
if mode['initial_arrival']=='require_at_install':
    # この分岐は別途確定してから定義する。推測による条件追加を禁止。
    raise RuntimeError('設置位置での到着条件追加は、専用の分岐定義と検証が必要')

# 取出し選択はBusy成立後に解除する。
for x,v in [(3,'BoxPacking_A_Busy'),(4,'BoxPacking_B_Busy')]:
    cs=[c for c in box[13]['CLs'] if c['__type']=='LD' and c.get('X',0)==x and c.get('Y',0)==0]
    assert len(cs)==1 and cs[0].get('Not');cs[0]['Var']=v

# 梱包後はZ上昇完了ONを確認して入数判定へ。独自の待ち時間や受付方式は追加しない。
c=box[36]['CLs'][1];assert c['Var']=='RCON2_4_MoveDone' and c.get('Not')
c.pop('Not')

# 箱内XY合流は、Y側移動工程（合流まで自己保持）と両軸完了で成立させる。
# 取出し後Z上昇工程はX移動開始で解除されるため、合流の開始元には使えない。
assert box[32]['CLs'][0]['Var']=='BoxPacking_M[34]'
box[32]['CLs'][0]['Var']='BoxPacking_M[36]'

# 前回の100ms完了保持を新しい移動の完了と誤認しないよう、開始枝だけでOFFを待つ。
# 自己保持枝は迂回させ、今回の移動完了ONで工程を落とさない。
for original_index,axis in [(11,5),(27,4),(35,4)]:
    r=box[original_index]
    for c in r['CLs']:
        if c.get('X',0)>=2:c['X']+=1
    for v in r['VLs']:
        if v.get('X',0)>=2:v['X']+=1
    r['CLs'] += [ld(f'RCON2_{axis}_MoveDone',2,nc=True),{'__type':'HL','X':2,'Y':1}]
    reindex(r)

# 満杯排出・軸戻り完了の立上りで、次箱用カウンタを0へ。
r=box[41]
r['CLs'] += [
    {'__type':'HL','X':4},
    {'__type':'F','Name':'Up','Id':str(uuid.uuid4()),'In':[{'__type':'PF','Arg':'In'}],'Out':[{'__type':'PF','Arg':''}],'X':3,'Y':1},
    {'__type':'F','Name':'MOVE','In':[{'__type':'PF','Arg':'EN'},{'__type':'PRM','Arg':'In','Type':'ANY','Var':'INT#0'}],'Out':[{'__type':'PF','Arg':'ENO'},{'__type':'PRM','Arg':'Out','Type':'ANY','Var':'Box_Total_CT'}],'X':4,'Y':1,'PL':True}]
r['VLs'].append({'X':3});reindex(r)

# A側の取出し待ちは、3枝が合流した後で共通解除する。
r=sf[31]
assert len([c for c in r['CLs'] if c['__type']=='ST' and c['Var']=='ST7_A_SF_Wait_Pickup'])==1
for c in r['CLs']:
    if c.get('X',0)>=2:c['X']+=1
# X2の縦線は新接点の入力側に残す。
r['CLs'].append(ld('BoxPacking_A_Pickup_Done',2,nc=True))
r['CMT']='【A側 取出し待ち】回転完了後に保持\r\n箱詰めA取出し・Z上昇完了で解除\r\n→次のストックフォルダ回転準備'
reindex(r)

done=newrow([ld('BoxPacking_M[20]'),ld('BoxPacking_M[2]',y=1),co('BoxPacking_M[2]')],[{'X':1}],
    '【初回確認完了】取出し先判定へ受渡し\r\nM[2]を保持し、通常運転中の初回再進入を防ぐ')
busy=newrow([ld('BoxPacking_M[1]'),ld('BoxPacking_Init_Busy',y=1),ld('BoxPacking_M[2]',1,nc=True),co('BoxPacking_Init_Busy',2)],[{'X':1}],
    '【初回確認中】開始から初回確認完了まで保持\r\nM[2]成立後に解除')
pickup=newrow([ld('BoxPacking_A_Busy'),ld('BoxPacking_M[34]',1),ld('RCON2_4_MoveDone',2),co('BoxPacking_A_Pickup_Done',3)],comment=
    '【A側取出し完了】チャック後のZ上昇完了\r\nRCON2_4：箱詰めZ軸\r\n→ST7 A側の取出し待ち保持を解除')

rows=[];old_to_new={}
for i,r in enumerate(box):
    old_to_new[i]=len(rows);rows.append(r)
    if i==0:rows.extend([done,busy])
    if i==27:rows.append(pickup)
assert len(rows)==45
N=lambda i:str(old_to_new[i])+'行'

# 大工程を#、分岐・合流を経路付きで表示。I/O・軸の用途も併記する。
comments={
0:'#【01 初回コンテナ確認】\r\n【開始】初回未完了・初回処理中でなければ開始',
1:'【初回状態分岐】RCON2_5：コンテナ設置・排出軸\r\n受渡・到着確認→'+N(2)+'／設置位置→'+N(13)+'\r\n排出位置→'+N(6)+'／位置未確定→'+N(8)+'\r\nX1003：コンテナ到着（受渡位置の判定に使用）',
2:'【初回設置準備】コンテナ排出シリンダー戻\r\nY1204：コンテナ排出戻',
3:'RCON2_5：コンテナ設置・排出軸→設置位置[2]\r\nX1016・X1018：排出1・2の戻完了を確認',
4:'【方向分岐】X1007：コンテナトレイ方向\r\n方向OK→'+N(13)+'：取出し先判定\r\n方向NGが10秒継続→'+N(5)+'：排出位置へ',
5:'【初回NG排出準備】RCON2_5：コンテナ設置・排出軸\r\n方向NGのコンテナを排出位置[3]へ',
6:'【初回排出】合流←'+N(1)+'：排出位置／'+N(5)+'：方向NG\r\nY1205：コンテナ排出行',
7:'X1005：コンテナ通過を確認\r\n→'+N(8)+'：コンテナ設置準備',
8:'#【02 コンテナ設置】\r\n【設置準備】合流←'+N(1)+'：位置未確定／'+N(7)+'・'+N(41)+'：排出完了\r\nRCON2_5：コンテナ設置・排出軸→受渡位置[1]\r\nX1010：空コンテナ送り戻確認のOFFで排出後から復帰',
9:'【受渡・到着確認】RCON2_5：コンテナ設置・排出軸\r\n受渡位置[1]・X1003：コンテナ到着を確認\r\nY1204：コンテナ排出戻',
10:'X1016・X1018：コンテナ排出1・2の戻完了\r\nY1206：箱入れチャック戻',
11:'X1020：箱入れチャック戻完了を確認\r\nRCON2_5：コンテナ設置・排出軸→設置位置[2]',
12:'【設置完了】RCON2_5：コンテナ設置・排出軸の移動完了\r\n→'+N(13)+'：取出し先判定',
13:'#【03 ワーク取出し】\r\n【取出し先分岐】合流←'+N(1)+'・'+N(4)+'・'+N(12)+'：準備完了／'+N(36)+'：80個未満\r\nST7の取出し待ちを選択。Busy成立まで判定・選択を保持\r\nA側優先→'+N(14)+'／既存B側分岐→'+N(15),
14:'【A側取出し中】選択を受けてBusy保持\r\n成立時にBox_Total_CTへ5個加算\r\n'+N(36)+'の継続信号、または排出完了で解除',
15:'【B側取出し中】選択を受けてBusy保持\r\n成立時にBox_Total_CTへ5個加算',
16:'【取出し準備】A・B選択の合流\r\nRCON2_4：箱詰めZ軸→上昇位置[1]',
17:'【A側取出し位置】RCON2_2：箱詰めX軸／RCON2_3：箱詰めY軸\r\n両軸をA側取出し位置[1]へ\r\n→'+N(18)+'：X完了／'+N(19)+'：Y完了',
18:'RCON2_2：箱詰めX軸のA側取出し移動完了',
19:'RCON2_3：箱詰めY軸のA側取出し移動完了',
20:'【A側XY合流】←'+N(18)+'：X完了＋'+N(19)+'：Y完了\r\n→'+N(25)+'：取出し下降',
21:'【B側取出し位置】RCON2_2：箱詰めX軸／RCON2_3：箱詰めY軸\r\n両軸をB側取出し位置[2]へ',
22:'RCON2_2：箱詰めX軸のB側取出し移動完了',
23:'RCON2_3：箱詰めY軸のB側取出し移動完了',
24:'【B側XY合流】←'+N(22)+'：X完了＋'+N(23)+'：Y完了\r\n→'+N(25)+'：取出し下降',
25:'【取出し下降】A・BのXY移動完了から合流\r\nRCON2_4：箱詰めZ軸→取出し下降位置[2]',
26:'RCON2_4：箱詰めZ軸の取出し下降完了\r\nY1207：箱入れチャック行',
27:'X1021：箱入れチャック行完了を確認\r\nRCON2_4：箱詰めZ軸→取出し後上昇位置[1]',
28:'#【04 箱内配置】\r\nRCON2_2：箱詰めX軸の目標位置をSTで選択\r\n開始位置[3]＋HMI_Box_X_Pitch_mm×列番号（0～3）',
29:'RCON2_3：箱詰めY軸の目標位置をSTで選択\r\n開始位置[3]＋HMI_Box_Y_Pitch_mm×行番号（0～3）',
30:'RCON2_2：箱詰めX軸の箱内移動完了',
31:'RCON2_3：箱詰めY軸の箱内移動完了',
32:'【箱内XY合流】←'+N(30)+'：X完了＋'+N(31)+'：Y完了\r\n→'+N(33)+'：箱内下降',
33:'RCON2_4：箱詰めZ軸→箱内下降位置[3]',
34:'RCON2_4：箱詰めZ軸の箱内下降完了\r\nY1206：箱入れチャック戻',
35:'X1020：箱入れチャック戻完了を確認\r\nRCON2_4：箱詰めZ軸→箱内配置後上昇位置[1]',
36:'#【05 入数判定・満杯排出】\r\nRCON2_4：箱詰めZ軸の上昇完了後に入数判定\r\n80個未満→'+N(13)+'：次取出し／80個→'+N(37)+'：満杯排出',
37:'【満杯排出準備】RCON2_5：コンテナ設置・排出軸\r\n満杯コンテナを排出位置[3]へ',
38:'RCON2_5：コンテナ設置・排出軸の移動完了\r\nY1205：コンテナ排出行',
39:'X1005：コンテナ通過を確認\r\nY1204：コンテナ排出戻',
40:'X1016・X1018：コンテナ排出1・2の戻完了\r\nRCON2_5：コンテナ設置・排出軸→受渡位置[1]',
41:'【満杯排出完了】RCON2_5：コンテナ設置・排出軸の戻り完了\r\n完了立上りでBox_Total_CTを0へ\r\n→'+N(8)+'：次のコンテナ設置（X1010：空コンテナ送り戻OFF）',
}
for old,cmt in comments.items():rows[old_to_new[old]]['CMT']=cmt

names={1:'初回確認開始',2:'初回確認完了',3:'初回コンテナ状態判定',4:'受渡位置・コンテナ到着',5:'コンテナ設置位置状態',6:'コンテナ排出位置状態',7:'コンテナ軸位置未確定',8:'Y1204 コンテナ排出戻',9:'コンテナ軸 初回設置移動',10:'コンテナ方向判定',11:'コンテナ方向OK',12:'方向NGコンテナ 排出移動',13:'初回コンテナ排出',14:'初回コンテナ通過確認',15:'コンテナ軸 受渡位置移動',16:'受渡位置・到着確認',17:'Y1206 箱入れチャック戻',18:'コンテナ軸 設置位置移動',19:'コンテナ設置完了',20:'取出し先判定中',21:'A側取出し選択',22:'B側取出し選択',23:'箱詰めZ 取出し準備上昇',24:'A側取出しXY移動',25:'A側取出しX完了',26:'A側取出しY完了',27:'A側取出しXY完了',28:'B側取出しXY移動',29:'B側取出しX完了',30:'B側取出しY完了',31:'B側取出しXY完了',32:'箱詰めZ 取出し下降',33:'Y1207 取出しチャック行',34:'箱詰めZ 取出し後上昇',35:'箱内X位置選択・移動',36:'箱内Y位置選択・移動',37:'箱内X移動完了',38:'箱内Y移動完了',39:'箱内XY移動完了',40:'箱詰めZ 箱内下降',41:'Y1206 箱内チャック戻',42:'箱詰めZ 箱内配置後上昇',43:'コンテナ入数判定',44:'80個未満・次取出し',45:'80個・満杯排出',46:'コンテナ軸 満杯排出移動',47:'Y1205 満杯コンテナ排出行',48:'Y1204 満杯排出後戻',49:'コンテナ軸 排出後受渡戻'}
ec=E.Element('ECs')
for n,comment in names.items():E.SubElement(ec,'EC',EK=f'[{n}]',C=comment)

scope=next(s for s in d['scopes'] if 'N=BoxPacking_M\t' in s['text'])
scope_text=scope['text']
def edit_line(line,values):
    body=line[2:];parts=body.split('\t');out=[];seen=set()
    for p in parts:
        key=p.split('=',1)[0]
        if key in values:out.append(key+'='+values[key]);seen.add(key)
        else:out.append(p)
    for key,val in values.items():
        if key not in seen:out.append(key+'='+val)
    return '++'+'\t'.join(out)

local_comments={'BoxPacking_A_Busy':'A側取出し・箱内配置中','BoxPacking_End':'満杯排出・軸戻り完了',
    'HMI_RCON2_2_OUT_TargetPos':'RCON2_2 箱詰めX位置 [mm]','HMI_RCON2_3_OUT_TargetPos':'RCON2_3 箱詰めY位置 [mm]',
    'HMI_RCON2_4_OUT_TargetPos':'RCON2_4 箱詰めZ位置 [mm]','HMI_RCON2_5_OUT_TargetPos':'RCON2_5 コンテナ軸位置 [mm]'}
newlines=[]
for line in scope_text.splitlines():
    if line.startswith('++D='):
        fields=dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p);name=fields['N']
        if name=='BoxPacking_M':line=edit_line(line,{'Com':'箱詰め工程','EC':E.tostring(ec,encoding='unicode')})
        elif name in local_comments:
            values={'Com':local_comments[name]}
            if name=='HMI_RCON2_3_OUT_TargetPos' and fields.get('EC'):
                root=E.fromstring(fields['EC'].encode('utf-8'))
                for element in root:
                    if element.get('EK')=='[1]':element.set('C','A(左側)フォルダストック 取出しPos')
                values['EC']=E.tostring(root,encoding='unicode')
            line=edit_line(line,values)
    newlines.append(line)
loc='\r\n'.join(newlines)+'\r\n'
newdef=''.join(f'++D=BOOL\tN={name}\tG=VAR\tR=0\tConst=0\tRO=0\tCom={comment}\r\n' for name,comment in [('BoxPacking_Init_Busy','初回コンテナ確認中'),('BoxPacking_A_Pickup_Done','A側取出し・Z退避完了')])
assert all('N='+n+'\t' not in scope_text for n in ['BoxPacking_Init_Busy','BoxPacking_A_Pickup_Done'])
assert loc.count('+GN=VAR_EXTERNAL')==1
loc=loc.replace('+GN=VAR_EXTERNAL',newdef+'+GN=VAR_EXTERNAL',1)

# RCON2の既存100msラダーを使い、2～5軸の経路を接続する。
# M[3]は既存許可・運転状態のAND、M[2]は開始後PEND OFFを確認した保持。
# 新しいST・タイマー時間は追加しない。既存通信STと許可設定値は不変。
axisnames={2:'箱詰めX軸',3:'箱詰めY軸',4:'箱詰めZ軸',5:'コンテナ設置・排出軸'}
request_counts={2:3,3:3,4:5,5:6};permit_rows={};receipt_rows={}
all_source=json.dumps(d['sections'],ensure_ascii=False)
for axis,count in request_counts.items():
    assert not re.search(r'RCON2_'+str(axis)+r'_M\[(?:2|3)\]',all_source)
    base=283+(axis-2)*40;label=f'RCON2_{axis}：{axisnames[axis]}'
    permit_vars=[('AutoMode',False),('Pause[1]',True),('M9999',True),('In_Sw_RESET',True),
        ('RCON2_CommOK',False),('RCON2_WriteEnable',False),('RCON2_LayoutConfirmed',False),('RCON2_ByteOrderConfirmed',False),
        (f'RCON2_AxisApply[{axis}]',False),(f'RCON2_MotionPermit[{axis}]',False),(f'RCON2_IN[{axis}].DataValid',False),
        (f'RCON2_EncodeOK[{axis}]',False),(f'RCON2_{axis}_Ready',False)]
    pcs=[ld(v,x,nc=nc) for x,(v,nc) in enumerate(permit_vars)]
    for name,op,const in [('Speed_mm_s','>','LREAL#0.0'),('AccDec_G','>','LREAL#0.0'),('PositionBand_mm','>=','LREAL#0.0')]:
        pcs.append({'__type':'F','Name':op,'In':[{'__type':'PF','Arg':'EN'},{'__type':'PRM','Arg':'In1','Type':'ANY_ELEMENTARY(except BOOL)','Var':f'RCON2_{axis}_OUT_{name}'},{'__type':'PRM','Arg':'In2','Type':'ANY_ELEMENTARY(except BOOL)','Var':const}],'Out':[{'__type':'PF','Arg':''}],'X':len(pcs)})
    pcs.append(co(f'RCON2_{axis}_M[3]',len(pcs)))
    permit_rows[base]=newrow(pcs,comment=f'#【{label}】\r\n自動開始許可：既存通信確認・軸許可・準備完了\r\n非常停止・一時停止・リセット中は不許可')
    for off in [0,1,2,3]:
        assert rcon[base+off]['CLs'][0]['Var']=='P_Off'
        rcon[base+off]['CLs'][0]['Var']='P_On'
        rcon[base+off]['CMT']=label+'\r\n'+rcon[base+off].get('CMT','').replace('（未接続）','').replace('#RCON2_'+str(axis)+' '+axisnames[axis].replace('軸',''),'').strip()
    for off in [20,21,22,23]:
        assert rcon[base+off]['CLs'][0]['Var']=='P_Off'
        rcon[base+off]['CLs'][0]['Var']=f'RCON2_IN[{axis}].DataValid'
        rcon[base+off]['CMT']=label+'\r\n'+rcon[base+off].get('CMT','').replace('（未接続）','')+'（入力有効時）'
    rcon[base+24]['CLs'][0]['Var']='P_On'
    rcon[base+24]['CMT']=label+'\r\n入力有効状態を監視'
    start=rcon[base+5]
    assert start['CLs'][1]['Var']=='P_Off'
    start['CLs'][1]['Var']=f'RCON2_{axis}_M[3]'
    for c in start['CLs']:
        if c.get('X',0)>=4:c['X']+=1
    start['CLs'].append(ld(f'RCON2_{axis}_M[3]',4))
    start['CMT']=label+'\r\n移動開始：既存Up＋TOFで100ms保持\r\n開始許可OFF時は内部Startを解除'
    reindex(start)
    # 開始保持の入力タイマーはMoveDone中にリセットし、次要求を取り直す。
    original=rcon[base+38]
    timer=deepcopy(next(c for c in original['CLs'] if c['__type']=='FB'))
    edge=deepcopy(next(c for c in original['CLs'] if c['__type']=='F' and c['Name']=='Up'))
    timer['X']=4;timer.pop('Y',None);edge['X']=5;edge.pop('Y',None)
    cs=[ld(f'RCON2_{axis}_Auto[{n+1}]',0,n) for n in range(count)]
    cs += [ld(f'RCON2_{axis}_Ready',1),ld(f'RCON2_{axis}_M[3]',2),ld(f'RCON2_{axis}_MoveDone',3,nc=True),timer,edge,
        ld(f'RCON2_{axis}_M[1]',0,count)]
    cs += [{'__type':'HL','X':x,'Y':count} for x in range(1,6)]
    cs += [ld(f'RCON2_{axis}_M[3]',6),ld(f'RCON2_{axis}_MoveDone',7,nc=True),co(f'RCON2_{axis}_M[1]',8)]
    vs=[{'X':1,'Y':y} for y in range(count-1)]+[{'X':6,'Y':y} for y in range(count)]
    rcon[base+38]=newrow(cs,vs,label+'\r\n自動要求[1]～['+str(count)+']を受けて開始保持\r\n前回完了100ms中は待ち、解除後に既存TONで確認')
    receipt_rows[base+38]=newrow([ld(f'RCON2_{axis}_M[1]'),ld(f'RCON2_{axis}_IN_PositionDone',1,nc=True),
        ld(f'RCON2_{axis}_M[2]',1,1),co(f'RCON2_{axis}_M[2]',2)],[{'X':1},{'X':2}],
        label+'\r\n今回移動の受付確認：開始保持中にPEND OFFを記憶\r\n開始保持解除で受付確認も解除')
    done_row=rcon[base+39]
    for c in done_row['CLs']:
        if c.get('X',0)>=1:c['X']+=1
    for v in done_row['VLs']:
        if v.get('X',0)>=1:v['X']+=1
    done_row['CLs'] += [ld(f'RCON2_{axis}_M[2]',1)] + [{'__type':'HL','X':x,'Y':1} for x in range(1,4)]
    done_row['CMT']=label+'\r\n今回受付済み＋PEND ONで移動完了\r\n既存TONで100ms保持'
    reindex(done_row)
rcon_new=[];rcon_row_map={}
for i,r in enumerate(rcon):
    if i in permit_rows:rcon_new.append(permit_rows[i])
    rcon_row_map[i]=len(rcon_new);rcon_new.append(r)
    if i in receipt_rows:rcon_new.append(receipt_rows[i])
assert len(rcon_new)==457

extra_scope_patches={}
for sc in d['scopes']:
    text=sc['text'];lines=[];changed=False
    for line in text.splitlines():
        if line.startswith('++D='):
            f=dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p)
            match=re.fullmatch(r'RCON2_([2-5])_M',f['N'])
            if match:
                root=E.fromstring(f.get('EC','<ECs/>').encode('utf-8'))
                bykey={e.get('EK'):e for e in root}
                for key,value in [('[2]','今回移動受付：PEND OFF確認'),('[3]','自動開始許可')]:
                    e=bykey.get(key)
                    if e is None:e=E.SubElement(root,'EC',EK=key)
                    e.set('C',value)
                line=edit_line(line,{'EC':E.tostring(root,encoding='unicode')});changed=True
        lines.append(line)
    if changed:extra_scope_patches[sc['part']]='\r\n'.join(lines)+'\r\n'
rcon_scope=next(sc for sc in d['scopes'] if 'N=RCON2_2_M\t' in sc['text'] and 'G=VAR_EXTERNAL' in next(l for l in sc['text'].splitlines() if 'N=RCON2_2_M\t' in l))
rt=extra_scope_patches[rcon_scope['part']]
if 'N=AutoMode\t' not in rt:
    rt+='++D=BOOL\tN=AutoMode\tG=VAR_EXTERNAL\tConst=0\tRO=0\tCom=自動運転\r\n'
extra_scope_patches[rcon_scope['part']]=rt

with ZipFile(io.BytesIO(raw)) as z:
    def encode(part,text):return (b'\xef\xbb\xbf' if z.read(part).startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
    patches={scope['part']:encode(scope['part'],loc)}
    patches.update({part:encode(part,text) for part,text in extra_scope_patches.items()})
    for name,newrows in [(boxname,rows),(sfname,sf),('RCON_IAI',rcon_new)]:
        part=sections[name]['part'];old=z.read(part).decode('utf-8-sig').splitlines(keepends=True)
        if name==sfname:
            text=''.join(line if i!=31 else json.dumps(newrows[i],ensure_ascii=False,separators=(',',':'))+'\r\n' for i,line in enumerate(old))
        else:text=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in newrows)
        patches[part]=encode(part,text)
    stream=io.BytesIO()
    with ZipFile(stream,'w') as w:
        w.comment=z.comment
        for info in z.infolist():w.writestr(copy(info),patches.get(info.filename,z.read(info.filename)))
    data=stream.getvalue()
    with ZipFile(io.BytesIO(data)) as w:
        assert w.testzip() is None and w.namelist()==z.namelist()
        changed=[n for n in z.namelist() if w.read(n)!=z.read(n)]
        assert set(changed)==set(patches)
stage=b/dest.name;stage.write_bytes(data)
report={'source':str(src),'staged':str(stage),'output':str(dest),'source_sha256':d['sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),
    'changed_parts':changed,'unchanged_parts':len(z.namelist())-len(changed),'box_part':sections[boxname]['part'],'sf_part':sections[sfname]['part'],'scope_part':scope['part'],
    'box_rows':45,'sf_rows':32,'rcon_rows':457,'rcon_part':sections['RCON_IAI']['part'],'rcon_scope_part':rcon_scope['part'],'rcon_old_to_new_rows':rcon_row_map,'old_to_new_rows':old_to_new,'new_variable_names':['BoxPacking_Init_Busy','BoxPacking_A_Pickup_Done'],'decisions':mode,
    'native_validation':None,'condition_validation':None,'independent_audit':None,'published':False}
(b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['staged','output_sha256','changed_parts','unchanged_parts','box_rows']},ensure_ascii=False))
