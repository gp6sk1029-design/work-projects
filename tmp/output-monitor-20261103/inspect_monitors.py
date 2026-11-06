"""最新D版の駆動用Auto接点と異常監視用Auto接点を照合する。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,re,hashlib,sys,collections
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261103D.smc2')
def key(variable,error=False):
 p=r'Output_(A|B|Share)_Error_(?:M|TON)\[(\d+)\]' if error else r'Output_(A|B|Share)_M\[(\d+)\]'
 m=re.fullmatch(p,variable)
 return (m[1],int(m[2])) if m else None
def auto(row):return [e for e in row['CLs'] if e.get('__type')=='LD' and re.fullmatch(r'.+_Auto\[\d+\]',e.get('Var',''))]
with zipfile.ZipFile(src) as z:
 assert z.testzip() is None
 targets=[]
 for p in z.namelist():
  if p.endswith('.oem'):
   for e in E.fromstring(z.read(p)).iter():
    if e.get('type')=='PouBody' and e.get('name')=='Output_出力':targets.append(p.rsplit('/',1)[0]+'/'+e.get('id')+'.xml')
 assert len(targets)==1
 part=targets[0];rows=[json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines()]
 drives={};monitors={}
 for i,row in enumerate(rows):
  for e in row['CLs']:
   if e.get('__type')=='ST':
    k=key(e.get('Var',''))
    if k and auto(row):assert k not in drives;drives[k]=i
    k=key(e.get('Var',''),True)
    if k:assert k not in monitors;monitors[k]=i
 assert set(drives)==set(monitors)
 pairs=[]
 for k,drive in drives.items():
  monitor=monitors[k];da=auto(rows[drive]);ma=auto(rows[monitor])
  expect=[e['Var'] for e in da];actual=[e['Var'] for e in ma]
  assert len(expect)==len(set(expect)) and len(actual)==len(set(actual))
  assert all(e.get('X',0)==0 and not e.get('Not',False) for e in ma)
  assert [e.get('Y',0) for e in ma]==list(range(len(ma)))
  missing=[v for v in expect if v not in actual];extra=[v for v in actual if v not in expect]
  pairs.append({'group':k[0],'index':k[1],'drive_row':drive,'monitor_row':monitor,'expected':expect,'existing':actual,'missing':missing,'extra':extra,'monitor_comment':rows[monitor].get('CMT','')})
 report={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'part':part,'parts':len(z.namelist()),'rows':len(rows),'pairs':pairs,'pair_count':len(pairs),'missing_rows':sum(bool(p['missing']) for p in pairs),'missing_contacts':sum(len(p['missing']) for p in pairs),'already_matching':sum(not p['missing'] and not p['extra'] for p in pairs),'extra_contacts':sum(len(p['extra']) for p in pairs)}
 (b/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY',json.dumps({k:v for k,v in report.items() if k!='pairs'},ensure_ascii=False))
 print('MISSING',json.dumps([p for p in pairs if p['missing'] or p['extra']],ensure_ascii=False))
