"""提案に必要な13系統だけを抽出し、複合条件と参照内容を確認する。"""
from pathlib import Path
import json,re,sys,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
d=json.loads((Path(__file__).resolve().parent/'inspection.json').read_text(encoding='utf-8'))
n=next(n for n in d['ladders'] if n.endswith('78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml'))
def walk(v):
 if isinstance(v,dict):
  yield v
  for x in v.values():yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)
for i,row in enumerate(d['ladders'][n]):
 flags=sorted(set(x.get('Var') for x in walk(row) if re.fullmatch(r'Error_M\[\d+\]',x.get('Var',''))))
 print('ROW',i,'CMT',repr(row.get('CMT')),'FLAGS',flags)
 if i in (11,12,18,19,20,21,22):
  print('LOGIC',json.dumps(row,ensure_ascii=False,separators=(',',':'))[:4500])
for table in d['tables'].values():
 for p in table:
  if p.get('G')=='VAR_GLOBAL' and p['N'] in ('ST2_A_Hgt_M','ST3_A_Dis1_M','ST4_A_Rev1_M','ST6_A_Rev2_M','ST7_A_Dis2_M','Error_M','Pause'):
   print('COMMENTS',p['N'],p.get('Com'),p.get('EC'))
