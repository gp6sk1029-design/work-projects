"""最新C版の段番号とOutputのPause配置を読み取り専用で確認する。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,re,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261103C.smc2')
with zipfile.ZipFile(src) as z:
 assert z.testzip() is None
 sections={}
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody' and e.get('name') in ['Destacker_段バラシ','Output_出力','RCON_IAI']:sections[e.get('name')]=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'
 assert len(sections)==3
 rows={s:[json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines()] for s,n in sections.items()}
 ds=[]
 for i,row in enumerate(rows['Destacker_段バラシ']):
  es=row['CLs'];ds.append({'row':i,'coils':[e['Var'] for e in es if e.get('__type')=='ST' and e.get('Var','').startswith('Destacker_M[')],'contacts':[e['Var'] for e in es if e.get('__type')=='LD' and e.get('Var','').startswith('Destacker_M[')]})
 pause=[]
 for i,row in enumerate(rows['Output_出力']):
  es=row['CLs'];stops=[e for e in es if e.get('__type')=='LD' and e.get('Var')=='M9999']
  for e in es:
   if e.get('__type')!='LD' or not re.fullmatch(r'Pause(?:\[\d+\])?',e.get('Var','')):continue
   x=e.get('X',0);y=e.get('Y',0)
   common=bool(stops and any(s.get('Y',0)==y and s.get('X',0)<x for s in stops))
   mode=[m for m in es if m.get('__type')=='LD' and m.get('Var')=='ManualMode' and m.get('X',0)==x and m.get('Y',0)>y]
   pause.append({'row':i,'var':e['Var'],'ix':e.get('Ix'),'x':x,'y':y,'Not':e.get('Not',False),'common':common,'same_x_manual':mode,'coils':[s.get('Var') for s in es if s.get('__type')=='ST'],'comment':row.get('CMT','')[:90]})
 report={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'parts':len(z.namelist()),'sections':sections,'destacker':ds,'output_row_count':len(rows['Output_出力']),'pause':pause}
 (b/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print('DESTACKER',json.dumps(ds,ensure_ascii=False))
 print('PAUSE_SUMMARY',json.dumps({'count':len(pause),'common':sum(p['common'] for p in pause),'existing_same_x_manual':sum(bool(p['same_x_manual']) for p in pause),'non_common':sum(not p['common'] for p in pause),'source_sha256':report['sha256']},ensure_ascii=False))
 print('COMMON',json.dumps([p for p in pause if p['common']],ensure_ascii=False))
 print('NONCOMMON_ROWS',json.dumps([p for p in pause if not p['common']][:8],ensure_ascii=False))
