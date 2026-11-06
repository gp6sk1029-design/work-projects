"""13行の選択解除を、選択ビットからBusy成立へ変更する案の条件検査。"""
from pathlib import Path
from copy import deepcopy
import json
b=Path(__file__).parent
# 既に保存ラダーから作った接続評価関数を利用し、既存反例の実行部分は読み込まない。
ns={'__file__':str(b/'check_flow.py')}
exec((b/'check_flow.py').read_text(encoding='utf-8').split('\nresults=[]')[0],ns)
original=ns['rows'];rung=ns['rung'];rows=deepcopy(original)
replaced=[]
for c in rows[13]['CLs']:
 if c['__type']=='LD' and c.get('Not') and c.get('Var') in ['BoxPacking_M[20]','BoxPacking_M[21]']:
  old=c['Var'];c['Var']='BoxPacking_A_Busy' if old.endswith('[20]') else 'BoxPacking_B_Busy';replaced.append([old,c['Var']])
assert len(replaced)==2
tests=[]
def scan(env,prev):
 rung(rows[13],env)
 for i,side in [(14,'A'),(15,'B')]:
  rung(rows[i],env);value=env[f'BoxPacking_{side}_Busy']
  if value and not prev[side]:env['Box_Total_CT']+=5
  prev[side]=value
 rung(rows[36],env)

for count in [5,75]:
 for previous in ['A','B']:
  for nextside in ['A','B','both','wait_then_A']:
   env={'Box_Total_CT':count,'BoxPacking_M[42]':True,'BoxPacking_M[43]':True,f'BoxPacking_{previous}_Busy':True}
   prev={'A':previous=='A','B':previous=='B'};frames=[]
   for n in range(10):
    env['ST7_A_SF_Wait_Pickup']=nextside in ['A','both'] or (nextside=='wait_then_A' and n>=5)
    env['ST7_B_SF_Wait_Pickup']=nextside in ['B','both']
    scan(env,prev)
    frames.append({k:env.get(k,False) for k in ['BoxPacking_M[19]','BoxPacking_M[20]','BoxPacking_M[21]','BoxPacking_M[43]','BoxPacking_A_Busy','BoxPacking_B_Busy','Box_Total_CT']})
   expected='B' if nextside=='B' else 'A'
   assert env['Box_Total_CT']==count+5
   assert env[f'BoxPacking_{expected}_Busy'] and not env[f'BoxPacking_{"B" if expected=="A" else "A"}_Busy']
   assert not env['BoxPacking_M[19]'] and not env['BoxPacking_M[20]'] and not env['BoxPacking_M[21]']
   tests.append({'initial_count':count,'previous_side':previous,'next':nextside,'expected':expected,'frames':frames})
for side in ['A','B']:
 env={'Box_Total_CT':0,'BoxPacking_M[18]':True,'ST7_A_SF_Wait_Pickup':side=='A','ST7_B_SF_Wait_Pickup':side=='B'};prev={'A':False,'B':False}
 for n in range(5):scan(env,prev)
 assert env['Box_Total_CT']==5 and env[f'BoxPacking_{side}_Busy']
result={'proposal_only':True,'replacements':replaced,'repeat_cases':len(tests),'initial_cases':2,'tests':tests,'scope':'関連4行の条件モデル。PLC全体や実機の検証ではない。'}
(b/'selection_proposal_cases.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('繰返し16ケース＋初回2ケースで選択Busy成立・5加算1回を確認。プログラム未編集。')
