"""実ラダーの条件を使い、初回再成立と次取出しの反例を検査する。"""
from pathlib import Path
from collections import defaultdict
import json
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
rows=next(s['rows'] for s in d['sections'] if s['name']=='BoxPacking_箱詰め')

def rung(row,env):
 edges=defaultdict(set)
 for v in row['VLs']:
  p=(v.get('X',0),v.get('Y',0));q=(p[0],p[1]+1);edges[p].add(q);edges[q].add(p)
 for c in row['CLs']:
  kind=c['__type'];allow=False
  if kind=='HL':allow=True
  if kind=='LD':allow=bool(env.get(c['Var'],False))!=c.get('Not',False)
  if kind=='F':
   if c.get('Name') in ['<','=']:
    vs=[p['Var'] for p in c['In'] if p['__type']=='PRM'];a=env[vs[0]];z=int(vs[1].split('#')[1]);allow=a<z if c['Name']=='<' else a==z
   else:allow=True
  if allow:edges[(c.get('X',0),c.get('Y',0))].add((c.get('X',0)+1,c.get('Y',0)))
 seen={(0,y) for y in range(max(c.get('Y',0) for c in row['CLs'])+1)};todo=list(seen)
 while todo:
  for p in edges[todo.pop()]-seen:seen.add(p);todo.append(p)
 updates={c['Var']:(c.get('X',0),c.get('Y',0)) in seen for c in row['CLs'] if c['__type']=='ST'}
 env.update(updates)
 return updates

results=[]
for side in ['A','B']:
 for count in [5,75]:
  env={'Box_Total_CT':count,'BoxPacking_M[42]':True,'BoxPacking_M[43]':True,f'BoxPacking_{side}_Busy':True,'ST7_A_SF_Wait_Pickup':side=='A','ST7_B_SF_Wait_Pickup':side=='B'}
  frames=[]
  for scan in range(4):
   for i in [13,14,15,36]:rung(rows[i],env)
   frames.append({k:bool(env.get(k,False)) for k in ['BoxPacking_M[19]','BoxPacking_M[20]','BoxPacking_M[21]','BoxPacking_M[43]','BoxPacking_A_Busy','BoxPacking_B_Busy']})
  assert frames[0]['BoxPacking_M[19]'] and not frames[0][f'BoxPacking_{side}_Busy']
  assert all(not v for v in frames[-1].values())
  results.append({'side':side,'count':count,'next_pickup_stalls_without_other_start_origin':True,'frames':frames})

env={'Auto_Com_Start':True,'TimerQ_In_SenCY_Empty_Container_CY_H':False}
rung(rows[0],env)
# 初回制限接点はすべてOFF、初回済みフラグのない場合の入口だけを検証する。
assert env['BoxPacking_M[1]']
results.append({'initial_entry_possible_with_Auto_Com_Start_held':True,'preconditions':'M2/M7/M12/M14/M18=OFF、X1010のTimerQ=OFF'})
(b/'condition_counterexamples.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('A/B各2ケースで次取出し入口消失の反例を確認。初回開始の再成立条件を確認。')
