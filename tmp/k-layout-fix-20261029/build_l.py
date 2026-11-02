"""重なった表示要求を独立行に分離し、元の停止/データ更新の回路形状を戻す。"""
from pathlib import Path
import collections,copy,hashlib,itertools,json,re,shutil,sys,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
PREV=json.loads((BASE.parent/'j-seven-fix-20261029/verification.json').read_text(encoding='utf-8-sig'))
SOURCE=Path(PREV['destination']);DEST=SOURCE.with_name(SOURCE.name.replace('20261029K','20261029L'))
STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'

def power(row,values):
 graph=collections.defaultdict(list)
 for c in row['CLs']:
  on=True
  if c['__type']=='LD':on=bool(values.get(c['Var'],False))!=c.get('Not',False)
  elif c.get('Name')=='Up':on=values.get('@Up:'+c['Id'],False)
  if on:
   x,y=c.get('X',0),c.get('Y',0);graph[(x,y)].append((x+1,y))
 for v in row['VLs']:
  a=(v.get('X',0),v.get('Y',0));b=(a[0],a[1]+1);graph[a].append(b);graph[b].append(a)
 max_y=max([c.get('Y',0) for c in row['CLs']]+[v.get('Y',0)+1 for v in row['VLs']])
 reached={(0,y) for y in range(max_y+1)};todo=list(reached)
 while todo:
  for b in graph[todo.pop()]:
   if b not in reached:reached.add(b);todo.append(b)
 return reached

def dump(rows):return ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in rows)

def build():
 assert not DEST.exists(),'既存L版を上書きしません'
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==PREV['output_sha256'],'K版が更新されています'
 with zipfile.ZipFile(SOURCE) as z:
  raw={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
 name=next(n for n in raw if n.endswith('78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml'))
 text=raw[name].decode('utf-8-sig');lines=text.splitlines(keepends=True);old=json.loads(lines[11]);main=copy.deepcopy(old)
 coils=[c for c in old['CLs'] if c.get('__type')=='ST' and re.fullmatch(r'HMI_Message_Request\[10[1-7]\]',c.get('Var',''))]
 assert len(coils)==7
 blank_y={c.get('Y',0) for c in coils}
 # 表示要求専用の枝・横線だけを除く。その行に他の処理があれば自動修正しない。
 assert all(c['__type'] in ('HL','ST') and (c['__type']=='HL' or c in coils) for c in old['CLs'] if c.get('Y',0) in blank_y)
 spurs={(c.get('X',0),c.get('Y',0)-1) for c in coils}
 assert len([v for v in old['VLs'] if (v.get('X',0),v.get('Y',0)) in spurs])==7
 def compact_y(y):return y-sum(b<=y for b in blank_y)
 main['CLs']=[c for c in main['CLs'] if c.get('Y',0) not in blank_y]
 for c in main['CLs']:c['Y']=compact_y(c.get('Y',0))
 wires=[]
 for v in old['VLs']:
  if (v.get('X',0),v.get('Y',0)) in spurs:continue
  start,end=compact_y(v.get('Y',0)),compact_y(v.get('Y',0)+1)
  if start==end:continue
  assert end==start+1
  w=copy.deepcopy(v);w['Y']=start;wires.append(w)
 assert len({(v.get('X',0),v.get('Y',0)) for v in wires})==len(wires)
 main['VLs']=wires
 requests=[]
 for number in range(101,108):
  station=number-100
  requests.append({'CLs':[{'__type':'LD','Ix':0,'Var':'Error_M[4]'},
                          {'__type':'LD','Ix':1,'Var':f'Ins_A_Cv_M[{station*2+4}]','X':1},
                          {'__type':'ST','Ix':2,'Var':f'HMI_Message_Request[{number}]','X':2}],
                   'LRI':3,'RRI':4,'VLs':[],
                   'CMT':('#搬送ワーク不一致 表示要求\r\n停止・ワーク情報更新とは別回路\r\n' if number==101 else '')+f'ST{station} 表示要求'})
 # 行の分離後も、停止やワーク情報の命令は変数・Up Idを含めて同一。
 def command_sig(c):
  a=copy.deepcopy(c)
  for k in ('X','Y'):a.pop(k,None)
  return json.dumps(a,sort_keys=True,ensure_ascii=False)
 old_main=[c for c in old['CLs'] if c['__type']!='HL' and c not in coils]
 new_main=[c for c in main['CLs'] if c['__type']!='HL']
 assert [command_sig(c) for c in old_main]==[command_sig(c) for c in new_main]
 assert main.get('CMT')==old.get('CMT')
 # 表示要求の入力はError_M[4]の更新結果と、書換えられないIns_A_Cv_Mだけ。
 assert all(c.get('Var','').startswith(('Error_M[4]','Pause[4]','Out_TDC_Stop','HMI_Message_Request')) for c in old['CLs'] if c['__type']=='ST')
 contacts=sorted({c['Var'] for c in old['CLs'] if c['__type']=='LD'})
 up_keys=sorted({'@Up:'+c['Id'] for c in old['CLs'] if c.get('Name')=='Up'})
 pulses=[tuple(False for _ in up_keys),tuple(True for _ in up_keys)]+[tuple(i==k for i in range(len(up_keys))) for k in range(len(up_keys))]
 cases=0
 old_commands=[c for c in old['CLs'] if c['__type'] in ('ST','F') and c not in coils]
 new_commands=[c for c in main['CLs'] if c['__type'] in ('ST','F')]
 for bits in itertools.product((False,True),repeat=len(contacts)):
  for pulse in pulses:
   values=dict(zip(contacts,bits));values.update(zip(up_keys,pulse))
   before,after=power(old,values),power(main,values)
   for a,b in zip(old_commands,new_commands):
    assert ((a.get('X',0),a.get('Y',0)) in before)==((b.get('X',0),b.get('Y',0)) in after)
   error_coil=next(c for c in main['CLs'] if c.get('__type')=='ST' and c.get('Var')=='Error_M[4]')
   now=dict(values);now['Error_M[4]']=(error_coil.get('X',0),error_coil.get('Y',0)) in after
   for row in requests:
    target=row['CLs'][-1]
    prior=next(c for c in coils if c['Var']==target['Var'])
    assert ((prior.get('X',0),prior.get('Y',0)) in before)==((target['X'],0) in power(row,now))
   cases+=1
 # 画面配置が安定していたG版の停止/データ更新構成とも照合（原本はKのまま）。
 g_report=json.loads((BASE.parent/'error-station-20261028/verification.json').read_text(encoding='utf-8-sig'))
 with zipfile.ZipFile(g_report['destination']) as z:
  gn=next(n for n in z.namelist() if n.endswith('78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml'))
  original=json.loads(z.read(gn).decode('utf-8-sig').splitlines()[11])
  for i,c in enumerate(original['CLs']):
   if c.get('Name')=='MOVE' and any(p.get('Var')=='HMI_MessageNo[0]' for p in c.get('Out',[])):
    original['CLs'][i]={'__type':'HL','X':c.get('X',0),'Y':c.get('Y',0)}
 def shape(row):
  t=copy.deepcopy(row)
  for c in t['CLs']:
   c.setdefault('X',0);c.setdefault('Y',0)
   def scrub(obj):
    if isinstance(obj,dict):
     obj.pop('Ix',None)
     for v in obj.values():scrub(v)
    elif isinstance(obj,list):
     for v in obj:scrub(v)
   scrub(c)
  t['CLs']=sorted(t['CLs'],key=lambda c:(c['Y'],c['X']))
  t['VLs']=sorted((v.get('X',0),v.get('Y',0)) for v in t['VLs'])
  return t['CLs'],t['VLs']
 assert shape(main)==shape(original),'G版の元の正常構成と異なる'
 replacement=dump([main]+requests)
 lines[11]=replacement
 raw[name]=(b'\xef\xbb\xbf' if raw[name].startswith(b'\xef\xbb\xbf') else b'')+''.join(lines).encode('utf-8')
 counts={}
 for n,data in raw.items():
  try:t=data.decode('utf-8-sig')
  except UnicodeError:continue
  if t.startswith('{"CLs"'):counts[n]=sum(bool(l.strip()) for l in t.splitlines())
 with zipfile.ZipFile(STAGED,'w') as z:
  z.comment=comment
  for info in infos:z.writestr(info,raw[info.filename])
 with zipfile.ZipFile(STAGED) as z,zipfile.ZipFile(SOURCE) as original_zip:
  assert z.testzip() is None and z.namelist()==original_zip.namelist()
  assert [n for n in z.namelist() if z.read(n)!=original_zip.read(n)]==[name]
  updated=z.read(name).decode('utf-8-sig').splitlines()
  old_lines=original_zip.read(name).decode('utf-8-sig').splitlines()
  assert updated[:11]==old_lines[:11] and updated[19:]==old_lines[12:]
 report={'source':str(SOURCE),'staged':str(STAGED),'destination':str(DEST),'source_sha256':PREV['output_sha256'],
         'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'changed_entries':[name],
         'changed_original_row':11,'independent_request_rows':list(range(12,19)),
         'checks':{'boolean_equivalence_cases':cases,'main_layout_matches_g_without_message_moves':True,
                   'stop_and_work_data_commands_and_up_ids_preserved':True,'other_original_rows_byte_preserved':True,
                   'all_other_archive_entries_byte_preserved':True,'all_new_request_rows_simple_series':True},
         'ladder_counts':counts,'native_validation':{},'native_connections':{},'application_display_verified':False,
         'hardware_transfer_performed':False}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'staged':str(STAGED),'checks':report['checks'],'rungs':sum(counts.values())},ensure_ascii=False))

def publish():
 r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
 assert r['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
 assert r['native_connections'].get('after_missing_connections')==0
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256']
 assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
 with STAGED.open('rb') as src,DEST.open('xb') as dst:shutil.copyfileobj(src,dst)
 print('保存完了：'+str(DEST))

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
