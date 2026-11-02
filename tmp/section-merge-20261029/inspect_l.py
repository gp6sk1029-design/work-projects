"""最新L版のセクション/宣言を読み取り、移動前の状態を固定する。"""
from pathlib import Path
import json,hashlib,sys,xml.etree.ElementTree as ET,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
prev=json.loads((BASE.parent/'k-layout-fix-20261029/verification.json').read_text(encoding='utf-8-sig'))
src=Path(prev['destination']);texts={};rows={};tables={}
with zipfile.ZipFile(src) as z:
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if '\x00' in t:continue
  texts[n]=t
  if t.startswith('[SLWD'):
   tables[n]=[dict(x.split('=',1) for x in l[2:].split('\t') if '=' in x) for l in t.splitlines() if l.startswith('++D=')]
  elif t.startswith('{"CLs"'):rows[n]=[json.loads(l) for l in t.splitlines() if l.strip()]
oem=next(n for n in texts if n.endswith('.oem'));root=ET.fromstring(texts[oem]);names={};programs={}
for e in root.iter('Entity'):
 if e.get('type')=='Program':programs[e.get('name')]=e.get('id')
 if e.get('type')=='PouBody' and e.get('subtype')=='Ladder':
  names[e.get('name')]=next(n for n in rows if n.endswith(e.get('id')+'.xml'))
result={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'texts':texts,'rows':rows,'tables':tables,'oem':oem,'names':names,'programs':programs}
(BASE/'inspection.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
for section in ('Error_エラー処理','HMI_Request_表示要求','ErrorCollect_異常収集'):
 print('SECTION',section)
 for i,row in enumerate(rows[names[section]]):
  if section=='Error_エラー処理' and not row.get('CMT','').startswith('#'):continue
  print(i,repr(row.get('CMT','')),[(c.get('__type'),c.get('Var')) for c in row['CLs'] if c.get('__type') in ('LD','ST')][:6])
print('HASH',result['sha256'])
