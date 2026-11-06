"""提案の局所検算と原本不変の確認。"""
from pathlib import Path
from itertools import product
from collections import Counter
import sys,json,runpy,copy,contextlib,io
b=Path(__file__).parent;out=Path('C:/Users/SEIGI-N13/work-projects/outputs/st7-dis2-review-20261106')
with contextlib.redirect_stdout(io.StringIO()):ns=runpy.run_path(str(b/'check.py'))
Model=ns['Model'];rows=ns['rows'];M=ns['M'];d=ns['d']
endrow={'CLs':[{'__type':'LD','Var':M(33)},{'__type':'LD','Var':'Out_CYw_Ejc_Hldr_Feed_A_H_Done','X':1},
 {'__type':'LD','Var':'ST7_A_Dis2_End','Y':1},{'__type':'HL','X':1,'Y':1},
 {'__type':'LD','Var':M(8),'Y':2},{'__type':'LD','Var':M(10),'X':1,'Y':2},
 {'__type':'LD','Var':'Retry[12]','Not':True,'X':2},{'__type':'LD','Var':'Ins_A_Next_Cycle','Not':True,'X':3},
 {'__type':'ST','Var':'ST7_A_Dis2_End','X':4}], 'VLs':[{'X':2},{'X':2,'Y':1}]}
cases=0
for real_end,empty,held,retry,nxt in product([False,True],repeat=5):
    a=Model({M(33):real_end,'Out_CYw_Ejc_Hldr_Feed_A_H_Done':True,M(8):empty,M(10):empty,'ST7_A_Dis2_End':held,'Retry[12]':retry,'Ins_A_Next_Cycle':nxt})
    a.row(endrow,'proposal');assert a.e['ST7_A_Dis2_End']==((real_end or empty or held) and not retry and not nxt);cases+=1
counter=Counter(c['Var'] for r in rows for c in r['CLs'] if c['__type']=='ST' and c.get('Var','').startswith('ST7_A_Dis2_M['))
assert set(counter)=={M(x) for x in range(1,34)} and set(counter.values())=={1}
proposed=copy.deepcopy(rows)
for r in proposed[8:9]:
    for c in r['CLs']:
        if c.get('X',0)>=5:c['X']=c.get('X',0)+1
    for v in r['VLs']:
        if v.get('X',0)>=5:v['X']=v.get('X',0)+1
    r['CLs'].append({'__type':'LD','Var':'ST7_A_Dis2_End','Not':True,'X':5})
a=Model({M(8):True})
for i in range(3):a.row(proposed[8],8);a.row(endrow,26)
assert a.e['ST7_A_Dis2_End'] and not a.e[M(8)] and not a.e[M(10)]
a.e['Ins_A_Next_Cycle']=True;a.row(endrow,26);assert not a.e['ST7_A_Dis2_End']
sys.path.insert(0,'C:/Users/SEIGI-N13/work-projects/.agents/skills/sysmac-studio/scripts');import sysmac as sm
p=sm.Project(d['path']);assert p.fingerprint==d['sha'], '分析中に原本が更新されたため再確認が必要'
versions=[]
for v in d['versions']:
    q=sm.Project(v['path']);assert q.fingerprint==v['sha'];versions.append({'name':v['name'],'sha256':q.fingerprint,'unchanged':True})
r={'date':'2026-11-06','selected':d['solution'],'versions':versions,'target_rows':32,'step_coils':'M1～33各1個','checked_conditions':len(ns['checks']),'proposed_end_boolean_cases':cases,'empty_end_release_trace_passed':True,'request_count':len(json.loads((b/'checks.json').read_text(encoding='utf-8'))['request_audit']),'actual_project_modified':False,'full_application_build':False,'plc_simulation':False,'machine_test':False,'pending_questions':['X214の検出対象','NG時に送り行完了を待つ必要性']}
sm.save_json(out/'検証結果.json',r)
for fname in ['checks.json','extra_checks.json']:(out/fname).write_bytes((b/fname).read_bytes())
memory=Path('C:/Users/SEIGI-N13/work-projects/MEMORY.md')
with memory.open('a',encoding='utf-8') as f:f.write('''
### 2026-11-06 ST7_A_Dis2左SF排出の問題点・対策案（生産技術主任補佐PDM_261102／Codex PLC分析担当）
- ユーザーがST6分析を中止後、ST7左SF排出の分析・丁寧な対策提案を依頼。最新登録J 85803125...／465a630d...の保存データを読取り。I対象節と全32行同一。前後J/I全ファイル指紋不変。実更新・PLC操作なし。
- 確認：10/19行RCON1_5_Auto2通常コイル二重で後段OFF上書き。25行送り戻Auto3はOutput106/108に接点0（Auto2は受け既存・書込元なし）。8行無ワークM10は完了経路なし、26EndはNextCycle解除なしで次回25M33も阻害。8正常枝B満杯NCと異常枝A満杯NO混在、18/27もB側参照。16のNG枝だけ送り行Done迂回。軸完了待ち8箇所は旧Done流用可、受け120/201のOR連続＋Up再受付と121/202のM1&PEND立上り問題が併存。
- 積数：14で配置前加算、Retry再進入で再加算、21で5→0が回転前。27に5段記憶なし、端位置両OFFではBusyだけ保持。17実式は基準TargetPos3、説明変数は2と不一致、9は2をコンベア回収へ使用。計算自体は1～5で基準+ピッチ*(CT-1)、0/6では18の目標転送不成立。想定外判定では15の送りのみ出る。
- 受け側仮止め：RCON86/167 StartのP_Off、上下162～165と左右82～84の数値転送P_Offは未変更。Retry11/12は有無満杯/軸異常の役割が別なので誤記扱いしない。待ち解除31の共通PickupDoneは維持。Bプログラム自体は対象外。
- 局所結線モデル12観点＋OR/旧Done追加反例、提案End全32条件と空ワーク終了→判定保持解除→Next解除を検算。工程コイルM1～33各1、対象要求15種類。機械結合・全体ビルド・PLCシミュレータ・実機未検証。X214検出対象とNG送り待ち条件をユーザーへ確認中。
- 成果物outputs/st7-dis2-review-20261106/問題点と対策案.txt、検証結果.json、checks.json、extra_checks.json。SKILL提案：通常コイル後段OFF、無ワーク完了、End次周期解除、積数と回転受渡しを標準検査へ。時間未計測・追加有料APIなし。
''')
print(json.dumps(r,ensure_ascii=False,indent=2))
