"""最新Jを取り込み、合意したST7対策を既存ラダー形式で候補へ反映する。"""
from pathlib import Path,PurePosixPath
from copy import deepcopy
from xml.etree import ElementTree as E
import json,re,sys,datetime
from ladder import *
b=Path(__file__).parent;d=json.loads((b/'snapshot.json').read_text(encoding='utf-8'))
live=sm.Project(d['path']);assert live.fingerprint==d['sha']
inside=sm.Project(d['backup']);external=sm.Project(d['base']);assert external.fingerprint==d['base_sha']
old=deepcopy(inside.section('ST7_A_Dis2_左SF排出')['rows']);r=deepcopy(old)
M=lambda n:f'ST7_A_Dis2_M[{n}]';SF=lambda n:f'ST7_A_SF_M[{n}]'
judge='Station_A_Data[7].Total_Judge';detail='Station_A_Data[7].Judgment_Details';ct='A_SF_CT';pitch='HMI_A_SF_StackPitch_mm'
full='TimerQ_In_Sen_SH_A_Ent';out_full='TimerQ_In_Sen_SH_A_Ext';sfbusy='ST7_A_SF_Busy';wait='ST7_A_SF_Wait_Pickup'
reset='In_Sw_RESET';nextcycle='Ins_A_Next_Cycle';ELEM=lambda name,*args:calc(name,list(args))
for k in range(34,47):
    assert not any(M(k) in json.dumps(s['rows']) for s in inside.sections),f'補助番号M{k}は使用済み'
assert any(c.get('Var')=='Out_CYw_Ejc_Hldr_Feed_A_F_Done' for c in r[16]['CLs']),'今回ユーザー修正済みの送り完了待ちを確認'

# 同じ工程番号は保ち、上下軸の要求のみ動作順1～5へ。
assert map_var(r[19],'RCON1_5_Auto[2]','RCON1_5_Auto[4]','ST')==1
assert map_var(r[22],'RCON1_5_Auto[4]','RCON1_5_Auto[5]','ST')==1
assert map_var(r[25],'Out_CYw_Ejc_Hldr_Feed_A_H_Auto[3]','Out_CYw_Ejc_Hldr_Feed_A_H_Auto[2]','ST')==1

# 有無判定：A側満杯へ修正。空ワークは満杯を待たず正常完了。
r[8]['CLs']=[c for c in r[8]['CLs'] if c.get('X',0)<5]+[st(M(8),5)]
r[8]['VLs']=[v for v in r[8]['VLs'] if v.get('X',0)<5]
common_column(r[8],5,ld('ST7_A_Dis2_End',5,nc=True))
common_column(r[8],6,ld(reset,6,nc=True))
common_column(r[8],7,ld(M(46),7))
initial_ready=row([ld(M(7)),ld('Out_CYw_Ejc_Hldr_Feed_A_H_Done',1),ld(M(46),y=1),hl(1,1),ld(nextcycle,2,nc=True),ld('ST7_A_Dis2_End',3,nc=True),st(M(46),4)],
    [vl(2)],'【今回の初期位置確認済み】\n初期の送り戻完了で保持\n初回走査のRetry解除だけでは判定しない\n完了・次サイクルで解除')
work_sensor='TimerQ_In_Sen_Work_A_Pos_07';work_data='Station_A_Data[7].Work_On';ngfull='TimerQ_In_Sen_NG2_Tray_A_Full'
has_work=any_row([[ld(M(8)),ld(ngfull,nc=True),ld(work_sensor),ELEM('=',work_data,'TRUE')]],M(9),cmt='【ワーク有：正常】\n【X209】：ワーク有・データ有\n【X212】：A側NG満杯では開始しない')
no_work=any_row([[ld(M(8)),ld(work_sensor,nc=True),ELEM('=',work_data,'FALSE')]],M(10),cmt='【ワーク無：正常】\n実物もデータもない場合は完了へ\nNG満杯の待機条件は掛けない')
mismatch=any_row([[ld(M(8)),ld(work_sensor,nc=True),ELEM('=',work_data,'TRUE')],[ld(M(8)),ld(work_sensor),ELEM('=',work_data,'FALSE')],[ld(M(8)),ld(ngfull),ld(work_sensor)],[ld(M(8)),ld(ngfull),ELEM('=',work_data,'TRUE')]],M(11),'set',[ld(reset,nc=True)],'【ワーク不一致・NG満杯】\n実物とデータの不一致を保持\nワークがある場合のA側NG満杯も保持')

# OKの加算は同じワークで1回だけ。Retryでは加算済み記憶を消さない。
for c in r[14]['CLs']:
    if c.get('Y',0)==2 and c['__type']=='F' and c.get('Name')=='Up':
        c.clear();c.update(ld(M(42),6,2,True))
count_latch=row([ld(M(17)),ld(M(18),1),st(M(42),2,mode='set')],[], '【今回ワークの加算済み】\nOK選択後に加算済みを保持\nRetryで同じワークを再加算しない')
sm.reindex(r[14])

# 新規投入は、満杯・回転中・設定不正を確認してから。NGで送り行は使用しない。
prefix=[ld(M(8)),ld(M(9)),ld(sfbusy,nc=True),ld(M(43),nc=True),ld(M(44),nc=True),ld('Retry[11]',nc=True)]
permit_terms=[]
for already in [False,True]:
    permit_terms.append(prefix+[ELEM('=',judge,'INT#1'),ld(full,nc=True),ld(M(42),nc=not already),ELEM('>=',ct,'INT#1' if already else 'INT#0'),ELEM('<=',ct,'INT#5' if already else 'INT#4'),ELEM('<>',pitch,'LREAL#0.0')])
for code in [4,5]:permit_terms.append(prefix+[ELEM('=',judge,'INT#9'),ELEM('=',detail,'INT#'+str(code))])
permit=any_row(permit_terms,M(45),cmt='【取出し開始の許可】\nOK：5個満杯・回転中は待機\nNG：送り行を使わず仕分け\n同じワークの再試行は再加算しない')
branch_column(r[9],2,ld(M(45),2),[1])

# 段数／ピッチ／行先未定は理由ビットへ保持する。物理軸範囲は未確認のため新規値を作らない。
pre=[ld(M(8)),ld(M(9))];ok=[ELEM('=',judge,'INT#1')]
bad_terms=[pre+[ELEM('<>',judge,'INT#1'),ELEM('<>',judge,'INT#9')],pre+[ELEM('=',judge,'INT#9'),ELEM('<>',detail,'INT#4'),ELEM('<>',detail,'INT#5')]]
bad_terms.extend([pre+ok+[ELEM('<',ct,'INT#0')],pre+ok+[ELEM('>',ct,'INT#5')],pre+ok+[ELEM('=',ct,'INT#5'),ld(M(42),nc=True),ld(full,nc=True),ld(sfbusy,nc=True)],pre+ok+[ld(M(42)),ELEM('<',ct,'INT#1')],pre+ok+[ELEM('=',pitch,'LREAL#0.0')]])
config_pre=any_row(bad_terms,M(43),'set',[ld(reset,nc=True)],'【設定・判定異常】\nOK段数・ピッチ未設定・行先未定\n異常はM[43]へ保持\nRESETで解除後、STARTで再確認')
post=[ld(M(22)),ld('RCON1_3_MoveDone')]
post2=[ld(M(23))]
post_terms=[]
for preface in [post,post2]:
    for bad in [ELEM('<',ct,'INT#1'),ELEM('>',ct,'INT#5'),ELEM('=',pitch,'LREAL#0.0')]:post_terms.append(preface+ok+[bad])
config_post=any_row(post_terms,M(43),'set',[ld(reset,nc=True)],'【積み位置の転送前確認】\n段数1～5・ピッチ設定を再確認\n異常時は下降を開始しない')

# A側5個満杯を使用。OK下降枝に回転中・設定異常の禁止を追加。
assert map_var(r[18],'TimerQ_In_Sen_SH_B_Ent',full)==1
# 共通のM23保持はそのまま。各数値転送枝の先頭へ条件を加える。
for c in r[18]['CLs']:
    if c.get('Y',0)>=1 and c.get('X',0)>=4:c['X']=c.get('X',0)+2
for v in r[18]['VLs']:
    if v.get('X',0)>=4:v['X']+=2
# M23コイルは維持し、その前から下へ分岐。追加禁止2接点の後で全行先へ分配。
r[18]['VLs'].append(vl(4))
r[18]['CLs'].extend([ld(M(43),4,1,True),ld(sfbusy,5,1,True)])
common_column(r[19],2,ld('Retry[11]',2,nc=True))
common_column(r[19],3,ld(M(43),3,nc=True))

# 8回の軸移動：今回工程でDone OFFを見てから新しいDone ONを使う。
guard_spec=[(4,34,5,5,'初期上昇'),(6,35,7,3,'初期左右'),(13,36,11,5,'回収下降'),(16,37,14,5,'保持後上昇'),(22,38,18,3,'仕分け左右'),(27,39,20,5,'配置下降'),(30,40,23,5,'解放後上昇'),(32,41,25,3,'左右戻り')]
guards={}
for phase,guard,target,axis,label in guard_spec:
    done=f'RCON1_{axis}_MoveDone'
    assert any(c.get('Var')==done and c['__type']=='LD' for c in r[target]['CLs'])
    branch_column(r[target],1,ld(M(guard),1),[1])
    guards[target]=row([ld(M(phase)),ld(done,1,nc=True),ld(M(guard),1,1),st(M(guard),2)],[vl(1),vl(2)],f'【{label}：今回完了の準備】\n工程中にMoveDone OFFを確認\nM[{guard}]へ保持し、次のONを待つ')

# 26行：実ワーク／空ワークの合流後、NextCycleで共通解除。
r[26]=row([ld(M(33)),ld('Out_CYw_Ejc_Hldr_Feed_A_H_Done',1),ld('ST7_A_Dis2_End',y=1),hl(1,1),ld(M(8),y=2),ld(M(10),1,2),ld('Retry[12]',2,nc=True),ld(nextcycle,3,nc=True),st('ST7_A_Dis2_End',4)],
    [vl(2),vl(2,1)],'【ST7完了の保持】\n送り戻り完了／正常なワークなしで合流\n次サイクルで全枝を共通解除')

# 回転準備：INはA側5個満杯、OutはA側取出し側5個有。両端の片方だけがON。
for oldvar,newvar in [('TimerQ_In_Sen_SH_B_Ent',full),('TimerQ_In_Sen_SH_B_Ext',out_full)]:assert map_var(r[27],oldvar,newvar)==1
# 同じ安全高さ比較2個のうち、後方を端位置の妥当性確認へ置換。
comp=[c for c in r[27]['CLs'] if c['__type']=='F' and c.get('Name')=='<'];assert len(comp)==2
comp[-1].clear();comp[-1].update(ld(SF(5),6))
branch_column(r[27],7,ld(M(44),7,nc=True),[1])
branch_column(r[27],8,ld(M(13),8,nc=True),[1])
branch_column(r[27],9,ld(M(27),9,nc=True),[1])
endpoint=any_row([[ld('TimerQ_In_SenCY_SH_A_Turn_H'),ld('TimerQ_In_SenCY_SH_A_Turn_F',nc=True)],[ld('TimerQ_In_SenCY_SH_A_Turn_H',nc=True),ld('TimerQ_In_SenCY_SH_A_Turn_F')]],SF(5),cmt='【回転端位置の確認】\n【X324】：ターン戻\n【X325】：ターン行\nどちらか片方だけONで開始可能')
turn_watch=row([ld(sfbusy),ld('Pause[1]',1,nc=True),ld(reset,2,nc=True),timer('ST7_A_SF_Watch_TON','T#10s',3)],[], '【フォルダ回転の時間監視】\n回転中から取出し待ち成立まで10秒\n一時停止・RESET中は計時しない')
turn_prefix=[ld('Auto_A_Start'),ld(full),ld(out_full,nc=True),ld(sfbusy,nc=True),ld(wait,nc=True),ELEM('<','RCON1_5_ActualPos_mm','RCON1_5_SafePos_mm')]
turn_errors=[turn_prefix+[ld('TimerQ_In_SenCY_SH_A_Turn_H',nc=True),ld('TimerQ_In_SenCY_SH_A_Turn_F',nc=True)],turn_prefix+[ld('TimerQ_In_SenCY_SH_A_Turn_H'),ld('TimerQ_In_SenCY_SH_A_Turn_F')],[ld('ST7_A_SF_Watch_TON.Q')]]
turn_error=any_row(turn_errors,M(44),'set',[ld(reset,nc=True)],'【回転異常の保持】\n回転端位置の両OFF／両ON\nまたは回転10秒未完了\nRESETで解除して再開')
for index,col in [(28,1),(29,3),(30,3)]:
    common_column(r[index],col,ld(M(44),col,nc=True))
    common_column(r[index],col+1,ld(reset,col+1,nc=True))
# 回転完了で新しい積み側の個数を0へ。待ちの自己保持中は繰り返さない。
turn_reset=row([ld(SF(3)),ld('Out_CYw_SH_A_Turn_H_Done',1),ld(SF(4),y=1),ld('Out_CYw_SH_A_Turn_F_Done',1,1),up(2),calc('MOVE',['INT#0'],ct,3)],
    [vl(2)],'【回転完了：新しい積み側へ】\n回転完了の立上りで個数を0へ\n取出し待ちの保持中は再クリアしない')
fault_reset=row([ld(reset),st(M(11),1,mode='reset'),st(M(43),1,1,'reset'),st(M(44),1,2,'reset')],[vl(1),vl(1,1)],'【ST7異常の解除】\n有無・設定・回転の保持をRESETで解除\n原因が残る場合は再検出')
count_reset=row([ld(nextcycle),st(M(42),1,mode='reset')],[], '【次ワークの加算準備】\n次サイクルで加算済み記憶を解除\nRetryでは保持して二重加算を防ぐ')

before={8:[initial_ready],18:[config_post],27:[endpoint,turn_watch,turn_error]}
# config_pre/permitはM8/M9を同一走査で使用するため8行の後へ置く。
after={8:[has_work,no_work,mismatch,config_pre,permit],14:[count_latch],31:[turn_reset,fault_reset,count_reset]}
rows=[];mapping={};guard_mapping={}
for i,rr in enumerate(r):
    rows.extend(before.get(i,[]))
    if i in guards:guard_mapping[i]=len(rows);rows.append(guards[i])
    mapping[i]=len(rows);rows.append(sm.reindex(rr))
    rows.extend(after.get(i,[]))

# RCON受け側：TON前のDone解除待ち、今回PEND OFFの記憶、今回PEND ON完了。
rcon=deepcopy(inside.section('RCON_IAI')['rows']);rcon_insert={}
for axis,start,finish in [(3,120,121),(5,201,202)]:
    req=rcon[start];done=f'RCON1_{axis}_MoveDone';mi=lambda n:f'RCON1_{axis}_M[{n}]';pend=f'RCON1_{axis}_IN_PositionDone'
    # 合流ORの最後へ[5]を追加（自己保持枝とは別）。
    if axis==5:
        for c in req['CLs']:
            if c.get('Y',0)>=4:c['Y']=c.get('Y',0)+1
        req['VLs'].append(vl(4,4));req['VLs'].append(vl(1,3))
        req['CLs'].append(ld('RCON1_5_Auto[5]',0,4))
    hold_y=5 if axis==5 else 3
    branch_column(req,2,ld(done,2,nc=True),[hold_y])
    req['CMT']=f'【今回要求の受付】\r\nRCON1_{axis}：A側SF/NG2'+('左右軸' if axis==3 else '上下軸')+'\r\n前Done解除後に既存TONで受付\r\n要求の切替を再受付できるようにする'
    comp=rcon[finish];branch_column(comp,1,ld(mi(2),1),[1])
    comp['CMT']=f'【今回の移動完了】\r\nRCON1_{axis}：今回PEND OFFを確認後\r\nPEND ONで完了を100ms保持'
    rcon_insert[finish]=row([ld(mi(1)),ld(pend,1,nc=True),ld(mi(2),1,1),st(mi(2),2)],[vl(1),vl(2)],f'【今回移動の受付確認】\nRCON1_{axis}：開始保持中のPEND OFFを記憶\n開始保持の解除で記憶を解除')
newrcon=[];rcon_mapping={}
for i,rr in enumerate(rcon):
    if i in rcon_insert:newrcon.append(rcon_insert[i])
    rcon_mapping[i]=len(newrcon);newrcon.append(sm.reindex(rr) if i in [120,121,201,202] else rr)

# 既存のST7停止ルートへ設定/回転異常を追加。制御の停止方式は変えない。
errors=deepcopy(inside.section('Error_エラー処理')['rows'])
errors[31]=row([ld(M(11)),ld(M(43),y=1),ld(M(44),y=2),ld('Error_ST7_A_M[0]',y=3),ld(reset,1,nc=True),st('Error_ST7_A_M[0]',2)],
    [vl(1),vl(1,1),vl(1,2)],'#【A側ST7 排出異常】\nワーク不一致・NG満杯・設定・回転異常\nRESETで解除、STARTで再確認\nRetry[11]：既存の停止・再試行経路')

# 行間コメントをI版の短い大中小構成へ。既存M番号は変えない。
cmts={0:'#【01 ST7排出の開始】\n【開始条件】\nA側開始・処理中でなければ開始\n自己保持はBusy条件を迂回',1:'【排出処理中の保持】\n開始から次サイクルまで保持',2:'【初期位置：チャックを戻す】\n【Y716】：排出チャック戻\nチャック戻完了で次の上昇へ',3:'【初期位置：上下軸を安全位置へ】\nRCON1_5：A側SF/NG2上下軸\n位置[1]を転送',4:'【初期上昇の移動要求】\nRCON1_5：上下軸 Auto[1]',5:'【初期位置：コンベア位置へ】\nRCON1_3：A側SF/NG2左右軸\n今回の上昇完了後、位置[1]を転送',6:'【左右原点の移動要求】\nRCON1_3：左右軸 Auto[1]',7:'【初期位置：送りを戻す】\n【Y718】：排出フォルダ送り戻',8:'#【02 ワーク有無の確認】\n【X209】：A側ワーク位置7\n実物とST7データを照合\n両方なしは正常完了へ\n【X212】：A側NG2満杯停止',9:'#【03 ワーク回収】\n【回収下降位置の転送】\nRCON1_5：A側SF/NG2上下軸\n位置[2]：コンベア回収下降\n満杯・回転・設定を確認して開始',10:'【回収下降の移動要求】\nRCON1_5：上下軸 Auto[2]',11:'【ワーク保持】\n【Y717】：排出チャック行\n今回の回収下降完了後に開始',12:'【保持後の安全上昇位置】\nRCON1_5：A側SF/NG2上下軸\n位置[1]を転送',13:'【保持後上昇の移動要求】\nRCON1_5：上下軸 Auto[3]',14:'#【04 OK・NGの行先選択】\nRCON1_3：A側SF/NG2左右軸\nOK：位置[2]、キズNG：[3]、姿NG：[4]\nOK段数はワークごとに1回だけ加算',15:'【OK品だけ送り行】\n【Y719】：排出フォルダ送り行\nNG品は送り行を使わない',16:'【仕分け左右の移動要求】\nRCON1_3：左右軸 Auto[2]\nOK：送り行完了を待って開始\nNG：送り行を使わず開始',17:'【OK積み位置の計算】\n基準：位置[3]、ピッチ：専用HMI変数\n目標＝基準＋ピッチ×(段数－1)',18:'【OK・NG下降位置の転送】\nRCON1_5：A側SF/NG2上下軸\nOK：位置[3]を1段目の基準に使用\nNG：キズ位置[7]、姿位置[8]\n【X214】：A側5個満杯では積まない',19:'【仕分け下降の移動要求】\nRCON1_5：上下軸 Auto[4]',20:'【配置後のワーク解放】\n【Y716】：排出チャック戻\n今回の下降完了後に開始',21:'#【05 回収位置へ復帰】\n【解放後の安全上昇位置】\nRCON1_5：上下軸 位置[1]\n5個目の解放後に積数を0へ',22:'【解放後上昇の移動要求】\nRCON1_5：上下軸 Auto[5]',23:'【左右原点位置の転送】\nRCON1_3：左右軸 位置[1]\n今回の上昇完了後に開始',24:'【左右原点の移動要求】\nRCON1_3：左右軸 Auto[3]',25:'【最後の送り戻し】\n【Y718】：排出フォルダ送り戻\n自動要求[2]はOutputへ接続済み',27:'#【06 5個の箱詰め側への受渡し】\n【X214】：積み側5個有\n【X215】：取出し側5個有\n取出し側が空き、上下軸が安全高さ\n回転端位置が正常なら開始',28:'【フォルダ回転中の保持】\n取出し待ち成立まで保持\nRESET・回転異常で解除',29:'【回転：戻り側へ】\n【Y726】：ストックフォルダターン戻\n【X325】：行位置から開始',30:'【回転：行側へ】\n【Y727】：ストックフォルダターン行\n【X324】：戻位置から開始',31:'【箱詰めA側の取出し待ち】\n回転完了で保持\n箱詰めのチャック・Z上昇完了で解除'}
for oldindex,text in cmts.items():rows[mapping[oldindex]]['CMT']=text.replace('\n','\r\n')
# 分岐の行番号は挿入後の現在位置で記載。
rows[mapping[8]]['CMT']+=f'\r\nワーク有 →{mapping[9]}行：回収\r\nワーク無 →{mapping[26]}行：完了'
rows[mapping[26]]['CMT']+=f'\r\n合流元：{mapping[25]}行／{mapping[8]}行'

sections={'ST7_A_Dis2_左SF排出':rows,'RCON_IAI':newrcon,'Error_エラー処理':errors}
ops=[]
def replace(part,data,label):
    if data==external.entries[part]:return
    file=b/(label+'.bin');file.write_bytes(data);ops.append({'op':'replace-part','part':part,'expected_sha256':sm.sha(external.entries[part]),'file':str(file.resolve())})
def encode(raw,text):return (b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
# 最新Jの全認識ラダーをベースへ照合して取り込む。無関係なユーザー更新も巻き戻さない。
for src in inside.sections:
    target=external.section(src['id']);rr=sections.get(src['name'],src['rows'])
    if src['name'] in sections:
        raw=inside.entries[src['part']];payload=encode(raw,'\r\n'.join(json.dumps(x,ensure_ascii=False,separators=(',',':')) for x in rr)+'\r\n')
    else:payload=inside.entries[src['part']]
    replace(target['part'],payload,'section_'+src['id'])

# 変数コメントと新規ローカルTON。宣言の追加は必要な外部参照とTONのみ。
comments={1:'排出動作開始',2:'初期チャック戻',3:'初期上昇位置転送',4:'初期上昇要求',5:'初期左右位置転送',6:'初期左右移動要求',7:'初期送り戻',8:'ワーク有無判定',9:'ワーク有',10:'ワーク無',11:'有無・NG満杯異常',12:'回収下降位置転送',13:'回収下降要求',14:'ワーク保持',15:'保持後上昇位置転送',16:'保持後上昇要求',17:'仕分け位置選択',18:'OK選択',19:'キズNG選択',20:'姿NG選択',21:'OK送り行開始',22:'仕分け左右移動中',23:'下降位置選択',24:'OK積み位置',25:'キズNG下降位置',26:'姿NG下降位置',27:'配置下降要求',28:'ワーク解放',29:'解放後上昇位置転送',30:'解放後上昇要求',31:'左右原点位置転送',32:'左右原点移動要求',33:'最後の送り戻',42:'今回ワーク加算済み',43:'積み設定・判定異常',44:'フォルダ回転異常',45:'ワーク回収開始許可',46:'今回の初期位置確認済み'}
for phase,guard,target,axis,label in guard_spec:comments[guard]=label+' 前完了解除'
auto5={1:'初期安全上昇',2:'コンベア回収下降',3:'保持後安全上昇',4:'仕分け先へ下降',5:'解放後安全上昇'}
var_added=[]
for part,txt in inside.variable_parts.items():
    lines=[];names=set()
    for line in txt.splitlines():
        if not line.startswith('++D='):lines.append(line);continue
        fields=dict(x.split('=',1) for x in line[2:].split('\t') if '=' in x);name=fields.get('N');names.add(name)
        ecmap=None;comment=None
        if name=='ST7_A_Dis2_M':ecmap={f'[{k}]':v for k,v in comments.items()}
        if name=='ST7_A_SF_M':ecmap={'[1]':'フォルダ回転開始','[2]':'フォルダ回転中','[3]':'ターン戻要求','[4]':'ターン行要求','[5]':'回転端位置正常'}
        if name=='RCON1_5_Auto':ecmap={f'[{k}]':v for k,v in auto5.items()}
        if name in ['RCON1_3_M','RCON1_5_M']:ecmap={'[2]':'今回PEND OFF確認'}
        if name=='HMI_RCON1_5_OUT_TargetPos':ecmap={'[1]':'安全上昇位置','[2]':'コンベア回収下降位置','[3]':'OK積み1段目の基準','[4]':'旧段別位置4：現在未使用','[5]':'旧段別位置5：現在未使用','[6]':'旧段別位置6：現在未使用','[7]':'キズNG下降位置','[8]':'姿NG下降位置'}
        if name=='HMI_A_SF_StackPitch_mm':comment='左SF積みピッチ [mm]'
        if name=='A_SF_StackTarget_mm':comment='基準[3]＋積みピッチ補正 [mm]'
        if name=='A_SF_StackStepOffset':comment='積み段数－1'
        if name=='A_SF_StackDelta_mm':comment='ピッチ×段数補正 [mm]'
        if name=='TimerQ_In_Sen_SH_A_Ent':comment='【X214】：A側積み側5個有'
        if name=='TimerQ_In_Sen_SH_A_Ext':comment='【X215】：A側取出し側5個有'
        if ecmap:
            ec=E.fromstring(fields.get('EC','<ECs/>'))
            for key,value in ecmap.items():
                item=next((x for x in ec if x.get('EK')==key),None)
                if item is None:item=E.SubElement(ec,'EC',{'EK':key})
                item.set('C',value)
            value=E.tostring(ec,encoding='unicode')
            line=re.sub(r'\tEC=[^\t\r\n]*',lambda m:'\tEC='+value,line) if '\tEC=' in line else line+'\tEC='+value
        if comment:line=re.sub(r'\tCom=[^\t\r\n]*',lambda m:'\tCom='+comment,line) if '\tCom=' in line else line+'\tCom='+comment
        lines.append(line)
    if part=='86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml':
        assert 'ST7_A_SF_Watch_TON' not in names
        idx=next(i for i,line in enumerate(lines) if line.startswith('+GN=VAR_EXTERNAL'));lines.insert(idx,'++D=TON\tN=ST7_A_SF_Watch_TON\tG=VAR\tR=0\tConst=0\tRO=0\tCom=フォルダ回転10秒監視');var_added.append('ST7_A_SF_Watch_TON')
        for name,comment in [(full,'【X214】：A側積み側5個有'),(out_full,'【X215】：A側取出し側5個有'),(reset,'リセットSW')]:
            if name not in names:lines.append('++D=BOOL\tN='+name+'\tG=VAR_EXTERNAL\tCom='+comment);var_added.append(name)
    target=next(k for k in external.variable_parts if PurePosixPath(k).name==PurePosixPath(part).name)
    newtext='\r\n'.join(lines)+'\r\n'
    replace(target,encode(inside.entries[part],newtext),'vars_'+PurePosixPath(part).stem)

name='3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261106A'
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
oem=next(k for k in external.entries if k.endswith('.oem'));text=external.entries[oem].decode('utf-8-sig')
match=re.search(r'<Entity\b[^>]*\btype="Solution"[^>]*>',text);assert match
tag=re.sub(r'\bname="[^"]*"','name="'+name+'"',match[0]);tag=re.sub(r'\bdateLastModified="[^"]*"','dateLastModified="'+now.strftime('%m/%d/%Y %H:%M:%S')+'"',tag)
text=text[:match.start()]+tag+text[match.end():];replace(oem,encode(external.entries[oem],text),'oem')
root=str(PurePosixPath(oem).with_suffix('.xml'));text=external.entries[root].decode('utf-8-sig')
text,n=re.subn(r'<Project>[^<]*</Project>','<Project>'+name+'</Project>',text);assert n==1
text,n=re.subn(r'<DateModified>[^<]*</DateModified>','<DateModified>'+now.isoformat()+'</DateModified>',text);assert n==1
replace(root,encode(external.entries[root],text),'project_meta')
for part,data in external.entries.items():
    if not part.endswith(('.manifest','.manifest2')):continue
    text=data.decode('utf-8-sig')
    text,n=re.subn(r'\bsolutionName="[^"]*"','solutionName="'+name+'"',text)
    if n:replace(part,encode(data,text),'manifest_'+PurePosixPath(part).suffix[1:])
sm.save_json(b/'plan.json',{'source_sha256':external.fingerprint,'operations':ops})
candidate=b/'A_candidate.smc2';serial=1
while candidate.exists():serial+=1;candidate=b/f'A_candidate_v{serial}.smc2'
meta={'source_internal':d['path'],'internal_sha':d['sha'],'base':d['base'],'base_sha':d['base_sha'],'backup':d['backup'],'solution':name,'destination':str(external.path.with_name(name+'.smc2')),'old_to_new_rows':mapping,'guard_rows':guard_mapping,'guard_spec':guard_spec,'rcon_old_to_new_rows':rcon_mapping,'new_local_and_external':var_added,'sections':sections,'old_user_row16':old[16],'stage':str(candidate),'hardware_unverified':True,'physical_start_P_Off_preserved':True}
sm.save_json(b/'build.json',meta)
assert live.current_fingerprint()==d['sha'] and external.current_fingerprint()==d['base_sha']
print(json.dumps({'stage':meta['stage'],'destination':meta['destination'],'ST7_rows':len(rows),'RCON_rows':len(newrcon),'new_variables':var_added},ensure_ascii=False,indent=2))
