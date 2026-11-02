"""同じ周期内で行を移す前に、越える命令との読取り・書込み競合を確認する。"""
import json,re,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
J=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))

def refs(row):
 reads=set();writes=set()
 def add(target,v):
  if v and '#' not in v and v not in ('TRUE','FALSE'):
   target.add(v)
 for c in row['CLs']:
  k=c['__type']
  if k=='LD':add(reads,c.get('Var'))
  elif k=='ST':
   add(writes,c.get('Var'))
   if c.get('S') or c.get('RS'):add(reads,c.get('Var'))
  elif k in ('F','FB'):
   for p in c.get('In',[]):add(reads,p.get('Var'))
   for p in c.get('Out',[]):add(writes,p.get('Var'))
   if k=='FB':add(reads,c.get('Var'));add(writes,c.get('Var'))
   if c.get('Name')=='Up':add(reads,'@Up:'+c.get('Id',''));add(writes,'@Up:'+c.get('Id',''))
  elif k=='IST':
   reads.add('@未知ST');writes.add('@未知ST')
 return reads,writes

def aliases(a,b):
 return a==b or a.startswith(b+'.') or b.startswith(a+'.') or a.startswith(b+'[') or b.startswith(a+'[')

def conflicts(a,b):
 ar,aw=refs(a);br,bw=refs(b)
 return [(x,y) for xs,ys in ((aw,br|bw),(ar,bw)) for x in xs for y in ys if aliases(x,y)]

def diag(row):
 return any(c.get('__type')=='ST' and re.fullmatch(r'Output_(?:A|B|Share)_Error_M\[\d+\]',c.get('Var','')) for c in row['CLs'])

if __name__=='__main__':
 st7=J['ladders'][J['names']['ST7_A_Dis2_左SF排出']]
 print('ST7_HAZARDS',[(i,k,conflicts(st7[i],st7[k])) for i in (9,10,11) for k in range(12,len(st7)) if conflicts(st7[i],st7[k])])
 output=J['ladders'][J['names']['Output_出力']]
 indices=[i for i,r in enumerate(output) if diag(r)]
 print('DIAGNOSTICS',len(indices))
 print('OUTPUT_HAZARDS',[(i,k,conflicts(output[i],output[k])) for i in indices for k in range(i+1,len(output)) if k not in indices and conflicts(output[i],output[k])])
