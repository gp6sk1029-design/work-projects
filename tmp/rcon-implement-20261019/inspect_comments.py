from pathlib import Path
import collections,json,re,sys,zipfile,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf8')
p=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261019B.smc2')
with zipfile.ZipFile(p) as z:
 ts={}
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if t.startswith('[SLWD'):ts[n]=t
 def fields(t):return [dict(k.split('=',1) for k in l[2:].split('\t') if '=' in k) for l in t.splitlines() if l.startswith('++D=')]
 gt=next(t for t in ts.values() if '+GN=VAR_GLOBAL' in t)
 g=fields(gt)
 rcon=[r for r in g if re.match(r'RCON[12]_',r['N'])]
 print('RCON',len(rcon),'empty',sum(not r.get('Com') for r in rcon),'arrays',[(r['N'],r['D'],'EC' in r) for r in rcon if r['D'].upper().startswith('ARRAY')])
 for prefix in ['E001_','E005_']:
  q=[r for r in g if re.match(prefix+r'(?:Out_OUT|In_IN)\d+_200[34]_',r['N'])]
  print(prefix,len(q),'mapped',sum('AT' in r for r in q),'unmapped',[(r['N'],r.get('Com')) for r in q if 'AT' not in r][:3])
 for n,t in ts.items():
  q=[r for r in fields(t) if r.get('EC')]
  if q:print('EC EXAMPLES',n,[(r['N'],r['D'],r['EC'][:450]) for r in q[:3]])
 print('C_EXISTS',p.with_name(p.stem[:-1]+'C.smc2').exists())
