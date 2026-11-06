from pathlib import Path
from collections import defaultdict
import json,re,copy,sys
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'));s={x['name']:x['rows'] for x in d['sections']};rows=s['Destacker_段バラシ']
src=(b.parent.parent/'box-cycle-implement-20261105/check_conditions.py').read_text(encoding='utf-8')
ns={'defaultdict':defaultdict,'re':re};exec(src[src.index('class Model:'):src.index('\nresults=[]')],ns);Model=ns['Model']
M=lambda n:f'Destacker_M[{n}]';done='RCON2_1_MoveDone';tests=[]
#①：Homeなどの4入力を確認済み状態で与え、確認OKと移動開始を検算。
for mask in range(16):
    home,supply,direction,stage=[bool(mask&(1<<i)) for i in range(4)]
    a=Model({M(13):True,'TimerQ_In_SenCY_Empty_Container_CY_H':home,'TimerQ_In_Sen_Supply_Container_Exist':supply,'TimerQ_In_Sen_Container_Direction_Check':direction,'TimerQ_In_Sen_Destacker_Stage_01_Exist':stage})
    a.row(rows[11]);a.row(rows[12])
    expected=home and not supply and direction and stage
    assert a.env[M(15)]==expected and a.env[M(16)]==expected
tests.append({'case':'11→12確認OKの4入力全組合せ','cases':16,'result':'確認OK条件に一致する時だけM16開始'})
# 復帰に時間がかかり、Upが先に消費される場合を2走査で確認。
a=Model({M(13):True,'TimerQ_In_Sen_Container_Direction_Check':True,'TimerQ_In_Sen_Destacker_Stage_01_Exist':True})
a.row(rows[11]);first=dict(a.env)
a.env['TimerQ_In_SenCY_Empty_Container_CY_H']=True;a.env['Out_CYw_Empty_Container_CY_H_Done']=True
a.row(rows[11]);a.row(rows[12]);assert not a.env[M(14)] and not a.env[M(16)]
tests.append({'case':'送り戻り到着がUpの次走査になる','first_M14':first[M(14)],'after_Home_and_EmptyDone':{k:a.env[k] for k in [M(14),M(15),M(16),'Out_CYw_Sep_Claw_H_Done','Out_CYw_Empty_Container_CY_H_Done']},'result':'誤った爪戻りDoneのままでは確認開始できない反例'})
fixed=copy.deepcopy(rows[11])
for c in fixed['CLs']:
    if c.get('Var')=='Out_CYw_Sep_Claw_H_Done':c['Var']='Out_CYw_Empty_Container_CY_H_Done'
a=Model({M(13):True,'TimerQ_In_Sen_Container_Direction_Check':True,'TimerQ_In_Sen_Destacker_Stage_01_Exist':True})
a.row(fixed);a.env['TimerQ_In_SenCY_Empty_Container_CY_H']=True;a.env['Out_CYw_Empty_Container_CY_H_Done']=True
a.row(fixed);a.row(rows[12]);assert a.env[M(16)]
tests.append({'case':'同じ反例でDone接点だけ送り戻りへ変更したコピー','result':'M14/M15/M16が成立。実プロジェクト未変更'})
# 異常監視は良否入力2通りずつで継続5秒後の結果確認。
for direction,stage in [(False,True),(True,False),(True,True)]:
    a=Model({M(13):True,'TimerQ_In_SenCY_Empty_Container_CY_H':True,'TimerQ_In_Sen_Container_Direction_Check':direction,'TimerQ_In_Sen_Destacker_Stage_01_Exist':stage})
    for _ in range(501):a.row(rows[11])
    assert a.env['Destacker_Error']==(not direction or not stage)
tests.append({'case':'11行の既存5秒異常監視','cases':3,'result':'方向NG/1段目無しで異常、両方OKでは異常なし。11行単体の条件モデル'})
#③：8行にDoneが足されたが、古いONか新しいONかは区別しない。
for value in [False,True]:
    a=Model({M(10):True,done:value});a.row(rows[8]);assert a.env[M(11)]==value
tests.append({'case':'8行のM10枝にDone追加','cases':2,'result':'Done OFFなら待つ。ONなら新旧を区別せず進む'})
a=Model({M(7):True,done:True});a.row(rows[5]);a.row(rows[6]);assert a.env[M(8)] and a.env[M(9)]
tests.append({'case':'5→6行、前移動のDoneがONのまま','result':'同走査でM8とM9がON。旧Done流用の反例は残る'})
assert not any(c.get('Var')==M(28) for sec in d['sections'] for r in sec['rows'] for c in r['CLs'])
#説明用4状態。開始前に補助ビットがOFF、工程終了後に再びOFFになる。
seen=False;timeline=[]
for label,active,value in [('開始直後・前の完了が残る',True,True),('前の完了が消える',True,False),('今回の移動が完了',True,True),('この工程が終了',False,True)]:
    seen=active and (not value or seen)
    timeline.append({'phase':label,'M8':int(active),'Done':int(value),'M28':int(seen),'next_allowed':bool(active and seen and value)})
assert [x['next_allowed'] for x in timeline]==[False,False,True,False]
p=sm.Project(d['internal']);e=sm.Project(d['external'])
out={'checks':tests,'explanation':timeline,'internal_sha':d['internal_sha256'],'internal_after':p.fingerprint,'internal_unchanged':p.fingerprint==d['internal_sha256'],'external_unchanged':e.fingerprint==d['external_sha256'],'scope':'保存ラダー配線の条件検算。実機・PLCシミュレータ未検証。実プロジェクト変更なし。'}
(b/'checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
