"""宣言スコープ、ラダー参照、埋込DBを限定して調査する。"""
from pathlib import Path
from zipfile import ZipFile
import sys,json,re,xml.etree.ElementTree as ET,sqlite3
sys.stdout.reconfigure(encoding='utf-8')
src=next(Path(r'C:\Users\SEIGI-N13\Desktop').glob('3089-2603A_*_20261023B.smc2'))
mode=sys.argv[1] if len(sys.argv)>1 else 'summary'
with ZipFile(src) as z:
 texts={}
 for n in z.namelist():
  try:texts[n]=z.read(n).decode('utf-8-sig')
  except UnicodeError:pass
 root=ET.fromstring(next(t for n,t in texts.items() if n.endswith('.oem')))
 parents={c:p for p in root.iter() for c in p}
 entities={e.get('id'):e for e in root.iter('Entity')}
 for n,t in texts.items():
  name=entities.get(Path(n).stem)
  label=name.get('name','?') if name is not None else '?'
  if t.startswith('[SLWD'):
   matches=[]
   for l in t.splitlines():
    if mode=='declarations': ok=re.search(r'\bN=(?:Stm_|Mtr_Flip|ST4_.*Origin|Origin_|Homing_|Auto_[AB]_Start|TimerQ_In_Sen_Work_[AB]_Pos_0[46])',l)
    else:ok=re.search(r'\bN=(?:Stm_|Mtr_Flip|ST4_.*Origin|Origin_)',l)
    if ok:matches.append(l)
   if matches:
    print('\nDECL',Path(n).name,label)
    print('\n'.join(matches))
  if mode=='summary' and t.lstrip().startswith('{'):
   rungs=[json.loads(l) for l in t.splitlines() if l.strip()]
   if label in ['Origin_原点復帰','CV2A_KED'] or any('Stm_' in json.dumps(r) for r in rungs):
    print('\nLADDER',Path(n).name,label,len(rungs))
    for i,r in enumerate(rungs):
     print(i,r.get('CMT',''),[(c.get('__type'),c.get('Name',''),c.get('Var'),c.get('Not',False)) for c in r['CLs'] if c.get('Var') or c.get('Name')])
 if mode=='db':
  n=next(n for n in z.namelist() if n.endswith('SysmacStudio.stsdb4'))
  b=z.read(n);print('DB HEADER',repr(b[:48]),len(b))
  if b.startswith(b'SQLite format 3'):
   db=sqlite3.connect(':memory:');db.deserialize(b)
   schema=list(db.execute("select name,sql from sqlite_master where type='table'"))
   for name,sql in schema:
    print('TABLE',name,sql)
    cur=db.execute('select * from "'+name+'"')
    cols=[d[0] for d in cur.description]
    for row in cur:
     matched=[(cols[i],str(v)[:350]) for i,v in enumerate(row) if isinstance(v,(str,bytes)) and (('_Swv_' in v or '旋回' in v) if isinstance(v,str) else b'_Swv_' in v)]
     if matched:print('MATCH ROW',[(cols[i],v) for i,v in enumerate(row) if not isinstance(v,(str,bytes)) or (isinstance(v,str) and len(v)<100)],matched)
 if mode=='entities':
  for key,e in entities.items():
   if e.get('type') in ['Pou','PouBody','VariableGroup'] or re.search('Origin|Stm|CV2',e.get('name','')):
    p=parents.get(e)
    while p is not None and p.tag!='Entity':p=parents.get(p)
    print(e.attrib,'PARENT',p.attrib if p is not None else None)
