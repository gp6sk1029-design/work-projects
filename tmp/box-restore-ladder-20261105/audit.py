"""独自ST撤回とD版との差分限定、既存開始回路の条件保持を独立確認。"""
from pathlib import Path
from zipfile import ZipFile
from collections import Counter,defaultdict
from copy import deepcopy
import itertools,json,re,hashlib
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
def rows(z,p):return [json.loads(l) for l in z.read(p).decode('utf-8-sig').splitlines()]
def powers(r,env):
 edges=defaultdict(set)
 for v in r['VLs']:
  a=(v.get('X',0),v.get('Y',0));c=(a[0],a[1]+1);edges[a].add(c);edges[c].add(a)
 for v in r['CLs']:
  x,y=v.get('X',0),v.get('Y',0)
  if v['__type'] in ['HL','F','FB'] or (v['__type']=='LD' and bool(env[v['Var']])!=v.get('Not',False)):edges[(x,y)].add((x+1,y))
 seen={(0,y) for y in range(max(v.get('Y',0) for v in r['CLs'])+1)};todo=list(seen)
 while todo:
  for node in edges[todo.pop()]-seen:seen.add(node);todo.append(node)
 return {(v['__type'],v.get('Id') or v.get('Var')):(v.get('X',0),v.get('Y',0)) in seen for v in r['CLs'] if v['__type'] in ['F','FB','ST']}
with ZipFile(m['baseline']) as d,ZipFile(m['staged']) as f,ZipFile(m['source']) as e:
 assert f.testzip() is None and f.namelist()==d.namelist()
 assert [n for n in d.namelist() if d.read(n)!=f.read(n)]==m['changes_from_D']
 oldr=rows(d,m['rcon_part']);newr=rows(f,m['rcon_part']);assert len(oldr)==len(newr)==449
 oldlines=d.read(m['rcon_part']).decode('utf-8-sig').splitlines();newlines=f.read(m['rcon_part']).decode('utf-8-sig').splitlines()
 assert [i for i,(a,c) in enumerate(zip(oldlines,newlines)) if a!=c]==[401,441]
 cases=0
 for i,axis,count in [(401,4,5),(441,5,6)]:
  # TON・Up・保持コイルと、Ready/MoveDone/自己保持接点を元と照合する。
  functions=lambda r:[{k:v for k,v in c.items() if k not in ['Ix','Y']} for c in r['CLs'] if c['__type'] in ['F','FB']]
  def without_ids(v):
   if isinstance(v,dict):return {k:without_ids(x) for k,x in v.items() if k!='Ix'}
   if isinstance(v,list):return [without_ids(x) for x in v]
   return v
  assert without_ids(functions(oldr[i]))==without_ids(functions(newr[i]))
  common=[f'RCON2_{axis}_Ready',f'RCON2_{axis}_M[1]',f'RCON2_{axis}_MoveDone']
  names=[f'RCON2_{axis}_Auto[{j}]' for j in range(1,count+1)]+common
  for values in itertools.product([False,True],repeat=len(names)):
   env=dict(zip(names,values));prev=dict(env)
   prev[f'RCON2_{axis}_Auto[1]']=any(env[f'RCON2_{axis}_Auto[{j}]'] for j in [1]+list(range(4,count+1)))
   assert powers(oldr[i],prev)==powers(newr[i],env);cases+=1
 oldbox=rows(d,m['box_part']);newbox=rows(f,m['box_part']);assert len(oldbox)==len(newbox)==42
 restore=deepcopy(newbox)
 expected=[(5,'RCON2_5_Auto[1]','RCON2_5_Auto[4]'),(11,'RCON2_5_Auto[2]','RCON2_5_Auto[5]'),(37,'RCON2_5_Auto[2]','RCON2_5_Auto[6]'),(38,'Out_CYw_Ejc_Cont_F_Auto[1]','Out_CYw_Ejc_Cont_F_Auto[2]'),(39,'Out_CYw_Ejc_Cont_H_Auto[1]','Out_CYw_Ejc_Cont_H_Auto[3]')]
 for i,old,new in expected:
  candidates=[c for c in restore[i]['CLs'] if c['__type']=='ST' and c.get('Var')==new];assert len(candidates)==1;candidates[0]['Var']=old
 assert restore[11]['CLs'][0]['Var']=='BoxPacking_M[16]';restore[11]['CLs'][0]['Var']='BoxPacking_M[14]'
 assert restore==oldbox,'番号・前工程接点以外にBoxの変更あり'
 for part in [m['box_part'],m['rcon_part'],m['output_part']]:
  texts=lambda z:[c['TXT'] for r in rows(z,part) for c in r['CLs'] if c['__type']=='IST']
  assert texts(d)==texts(f),'追加STが残っている'
 assert f.read(m['output_part'])==e.read(m['output_part']),'検証済みのOutput OR追加を保持'
 reqs=Counter(c['Var'] for r in newbox for c in r['CLs'] if c['__type']=='ST' and '_Auto[' in c.get('Var',''))
 assert all(n==1 for n in reqs.values())
 reads={c.get('Var') for r in newr+rows(f,m['output_part']) for c in r['CLs'] if c['__type']=='LD'}
 assert set(reqs)<=reads
m['independent_audit']={'new_ST_removed':True,'all_original_ST_texts_unchanged':True,'RCON_rows':449,'Box_rows':42,'RCON_changed_rows_only':[401,441],'RCON_OR_equivalence_cases':cases,'D_start_done_timers_unchanged':True,'D_variable_tables_unchanged':True,'D_counter_and_interlocks_unchanged':True,'requests_unique_and_received':True,'Box_changes_only_6_references':True}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(m['independent_audit'],ensure_ascii=False))
