"""M版の出力回路と監視回路を実変数で照合する読取り調査。"""
from pathlib import Path
import hashlib,json,re,sys,xml.etree.ElementTree as ET,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
previous=json.loads((BASE.parent/'section-merge-20261029/verification.json').read_text(encoding='utf-8-sig'))
src=Path(previous['destination']);texts={};rows={}
with zipfile.ZipFile(src) as z:
 assert z.testzip() is None
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if '\x00' in t:continue
  texts[n]=t
  if t.startswith('{"CLs"'):rows[n]=[json.loads(l) for l in t.splitlines() if l.strip()]
oem=next(n for n in texts if n.endswith('.oem'));root=ET.fromstring(texts[oem]);names={}
for e in root.iter('Entity'):
 if e.get('type')=='PouBody' and e.get('subtype')=='Ladder':
  names[e.get('name')]=next(n for n in rows if n.endswith(e.get('id')+'.xml'))
result={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'texts':texts,'rows':rows,'names':names,'oem':oem}
(BASE/'inspection.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
rr=rows[names['Output_出力']]
for i,r in enumerate(rr):
 coils=[c.get('Var','') for c in r['CLs'] if c.get('__type')=='ST']
 timers=[c.get('Var','') for c in r['CLs'] if c.get('__type')=='FB']
 print(i,'COIL='+','.join(coils),'FB='+','.join(timers),'COMMENT='+r.get('CMT','').replace('\r\n',' / ')[:90])
print('SOURCE',src,'SHA256',result['sha256'],'SECTIONS',len(rows),'RUNGS',sum(map(len,rows.values())))
