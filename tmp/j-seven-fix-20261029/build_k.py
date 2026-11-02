"""J版Error11行の7コイルに右母線までの横接続だけを補い、K版を作る。"""
from pathlib import Path
import collections,copy,hashlib,itertools,json,random,re,shutil,sys,zipfile

sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
DIAG=json.loads((BASE.parent/'j-crash-diagnosis-20261029/diagnosis.json').read_text(encoding='utf-8-sig'))
SOURCE=Path(DIAG['J']['path']);DEST=SOURCE.with_name(SOURCE.name.replace('20261029J','20261029K'))
STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'

def powered(row,values):
 graph=collections.defaultdict(list)
 for c in row['CLs']:
  condition=True
  if c['__type']=='LD':condition=bool(values.get(c['Var'],False))!=c.get('Not',False)
  elif c.get('Name')=='Up':condition=values.get('@Up:'+c['Id'],False)
  if condition:
   x,y=c.get('X',0),c.get('Y',0);graph[(x,y)].append((x+1,y))
 for v in row['VLs']:
  a=(v.get('X',0),v.get('Y',0));b=(a[0],a[1]+1);graph[a].append(b);graph[b].append(a)
 end_y=max([c.get('Y',0) for c in row['CLs']]+[v.get('Y',0)+1 for v in row['VLs']])
 reached={(0,y) for y in range(end_y+1)};pending=list(reached)
 while pending:
  for node in graph[pending.pop()]:
   if node not in reached:reached.add(node);pending.append(node)
 return reached

def build():
 assert not DEST.exists(),'既存K版は上書きしません'
 source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
 assert source_hash==DIAG['J']['sha256'],'診断後にJ版が更新されています'
 with zipfile.ZipFile(SOURCE) as z:
  assert z.testzip() is None
  raw={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
 name=next(n for n in raw if n.endswith('78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml'))
 text=raw[name].decode('utf-8-sig');lines=text.splitlines(keepends=True)
 before=json.loads(lines[11]);after=copy.deepcopy(before)
 coils=[c for c in after['CLs'] if c.get('__type')=='ST' and re.fullmatch(r'HMI_Message_Request\[10[1-7]\]',c.get('Var',''))]
 assert len(coils)==7
 end_x=max(c.get('X',0) for c in before['CLs'])
 occupied={(c.get('X',0),c.get('Y',0)) for c in before['CLs']}
 added=[]
 for coil in coils:
  x,y=coil.get('X',0),coil.get('Y',0)
  assert x<end_x
  # 横接続が別の縦線を横切る場合は短絡を生む可能性があるため中断する。
  assert not any(v.get('X',0)>x and v.get('X',0)<=end_x and v.get('Y',0) in (y-1,y) for v in before['VLs'])
  for column in range(x+1,end_x+1):
   assert (column,y) not in occupied
   cell={'__type':'HL','X':column,'Y':y};added.append(cell);after['CLs'].append(cell)
 assert len(added)==14
 assert after['CLs'][:-14]==before['CLs']
 assert {k:v for k,v in before.items() if k!='CLs'}=={k:v for k,v in after.items() if k!='CLs'}
 # 有効な既存命令の位置・変数・パラメータ・Ix/Up Idは1つも変更しない。
 assert [c for c in before['CLs'] if c['__type']!='HL']==[c for c in after['CLs'] if c['__type']!='HL']
 contacts=sorted({c['Var'] for c in before['CLs'] if c['__type']=='LD'})
 pulses=sorted({'@Up:'+c['Id'] for c in before['CLs'] if c.get('Name')=='Up'})
 pulse_vectors=[tuple(False for _ in pulses),tuple(True for _ in pulses)]
 pulse_vectors += [tuple(i==k for i in range(len(pulses))) for k in range(len(pulses))]
 targets={(c.get('X',0),c.get('Y',0)) for c in before['CLs'] if c['__type'] in ('LD','ST','F','FB')}
 cases=0
 for bits in itertools.product((False,True),repeat=len(contacts)):
  for pulse_bits in pulse_vectors:
   values=dict(zip(contacts,bits));values.update(zip(pulses,pulse_bits))
   old,new=powered(before,values),powered(after,values)
   assert old&targets==new&targets
   cases+=1
 rng=random.Random(20261029)
 for _ in range(4096):
  values={key:bool(rng.getrandbits(1)) for key in contacts+pulses}
  assert powered(before,values)&targets==powered(after,values)&targets
  cases+=1
 lines[11]=json.dumps(after,ensure_ascii=False,separators=(',',':'))+('\r\n' if lines[11].endswith('\r\n') else '\n')
 raw[name]=(b'\xef\xbb\xbf' if raw[name].startswith(b'\xef\xbb\xbf') else b'')+''.join(lines).encode('utf-8')
 ladder_counts={}
 for entry,data in raw.items():
  try:t=data.decode('utf-8-sig')
  except UnicodeError:continue
  if t.startswith('{"CLs"'):
   rr=[json.loads(l) for l in t.splitlines() if l.strip()];ladder_counts[entry]=len(rr)
 with zipfile.ZipFile(STAGED,'w') as z:
  z.comment=comment
  for info in infos:z.writestr(info,raw[info.filename])
 with zipfile.ZipFile(STAGED) as z,zipfile.ZipFile(SOURCE) as old:
  assert z.testzip() is None and z.namelist()==old.namelist()
  changed=[n for n in z.namelist() if z.read(n)!=old.read(n)]
  assert changed==[name],changed
 report={'source':str(SOURCE),'staged':str(STAGED),'destination':str(DEST),'source_sha256':source_hash,
         'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'changed_entries':[name],
         'changed_row':11,'fixed_coils':sorted(c['Var'] for c in coils),'added_horizontal_cells':added,
         'checks':{'existing_instruction_state_and_ids_unchanged':True,'other_rows_and_archive_entries_unchanged':True,
                   'no_vertical_crossings_added':True,'boolean_power_cases':cases,'variable_io_task_and_sections_unchanged':True},
         'ladder_counts':ladder_counts,'native_validation':{},'native_connections':{},'application_display_verified':False,
         'hardware_transfer_performed':False}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'staged':str(STAGED),'fixed_coils':report['fixed_coils'],'added_horizontal_cells':len(added),
                   'boolean_power_cases':cases,'rungs':sum(ladder_counts.values())},ensure_ascii=False))

def publish():
 r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
 assert r['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
 assert r['native_connections'].get('after_missing_connections')==0
 assert r['native_connections'].get('fixed_coils_connected')==7
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256']
 assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
 with STAGED.open('rb') as src,DEST.open('xb') as dst:shutil.copyfileobj(src,dst)
 assert hashlib.sha256(DEST.read_bytes()).hexdigest()==r['output_sha256']
 print('保存完了：'+str(DEST))

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
