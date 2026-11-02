"""各出力の制御・完了直後へ既存監視を配置する。条件と行内配線は変更しない。"""
from pathlib import Path
import collections,copy,hashlib,json,shutil,sys,zipfile
from audit_order import BASE,J,RR,mapping
sys.stdout.reconfigure(encoding='utf-8')
SOURCE=Path(J['source'])
DEST=SOURCE.with_name(SOURCE.name.replace('20261029M','20261029N'))
STAGED=BASE/DEST.name
REPORT=BASE/'verification.json'

def no_comment(row):
 r=copy.deepcopy(row);r.pop('CMT',None);return r

def banner(title,old):
 return '\r\n'.join(('# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━','# 【'+title+'】','#','# 目的：出力・完了判定・異常監視を出力ごとに配置','# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',old))

def build():
 assert not DEST.exists(),'既存N版は上書きしません'
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==J['sha256'],'M版が更新されています'
 m=mapping();assert not m['hazards'],m['hazards']
 out=J['names']['Output_出力'];new=copy.deepcopy([RR[i] for i in m['order']])
 positions={old:new for new,old in enumerate(m['order'])}
 # 末尾一括監視の見出しは廃止し、個別監視行を短く統一。
 for key,old in m['monitors'].items():
  row=new[positions[old]]
  timers=[c for c in row['CLs'] if c.get('__type')=='FB']
  assert len(timers)==1
  pt=[p['Var'] for p in timers[0]['In'] if p.get('Arg')=='PT']
  assert pt==['T#10s']
  row['CMT']='異常監視（自動指令・到達待ち10秒）'
 # 既存の大項目だけ共通見出しへ。各出力の個別説明は保持。
 titles={16:'A(左側) 供給ユニット｜シリンダ',28:'B(右側) 供給ユニット｜シリンダ',40:'A(左側) 検査・排出ユニット｜シリンダ',112:'B(右側) 検査・排出ユニット｜シリンダ',184:'共通 コンテナ部｜シリンダ',208:'A(左側) 受渡送り｜シリンダ',212:'B(右側) 受渡送り｜シリンダ'}
 for old,title in titles.items():
  row=new[positions[old]]
  original=row.get('CMT','')
  # 旧大項目見出しだけを除き、I/O個別行の説明は残す。
  lines=original.splitlines();io=[i for i,line in enumerate(lines) if line.startswith('【Y')]
  assert len(io)==1,(old,original)
  row['CMT']=banner(title,'\r\n'.join(lines[io[0]:]))
 assert len(new)==len(RR)==316
 for i,old in enumerate(m['order']):assert no_comment(new[i])==no_comment(RR[old]),old
 assert collections.Counter(json.dumps(no_comment(r),sort_keys=True) for r in new)==collections.Counter(json.dumps(no_comment(r),sort_keys=True) for r in RR)
 for key,old in m['monitors'].items():
  assert positions[old]==positions[m['done'][key]]+1==positions[m['controls'][key]]+2
 monitor_order=[i for i in m['order'] if i in m['monitors'].values()]
 assert monitor_order==sorted(m['monitors'].values()),'監視同士の元の優先順を保持'
 with zipfile.ZipFile(SOURCE) as source:
  assert source.testzip() is None
  raw=source.read(out)
  updated=(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in new)).encode('utf-8')
  if raw.startswith(b'\xef\xbb\xbf'):updated=b'\xef\xbb\xbf'+updated
  with zipfile.ZipFile(STAGED,'w') as z:
   z.comment=source.comment
   for info in source.infolist():z.writestr(info,updated if info.filename==out else source.read(info.filename))
 with zipfile.ZipFile(SOURCE) as original,zipfile.ZipFile(STAGED) as z:
  assert z.testzip() is None and z.namelist()==original.namelist()
  changed=[n for n in z.namelist() if z.read(n)!=original.read(n)]
  assert changed==[out]
  reread=[json.loads(line) for line in z.read(out).decode('utf-8-sig').splitlines() if line.strip()]
  assert reread==new
 placements=[{'side':key[0],'index':key[1],'control_old':m['controls'][key],'completion_old':m['done'][key],'monitor_old':old,'control_new':positions[m['controls'][key]],'completion_new':positions[m['done'][key]],'monitor_new':positions[old]} for key,old in m['monitors'].items()]
 report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':J['sha256'],'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'changed_entries':changed,'ladder_counts':{n:len(rows) for n,rows in J['rows'].items()},'new_declarations':[],'native_validation':{},'native_variables':{},'native_connections':{},'checks':{'groups':100,'groups_by_side':dict(collections.Counter(k[0] for k in m['controls'])),'crossed_rung_pairs':len(m['crossings']),'dependency_hazards':m['hazards'],'all_control_completion_monitor_adjacent':True,'all_original_instructions_and_geometry_unchanged':True,'monitor_relative_priority_unchanged':True,'only_output_entry_modified':True,'shared_timers_preserved':m['shared_timers'],'existing_start_mismatches_preserved':m['start_mismatches'],'existing_raw_sensor_reference_preserved':m['unfiltered_inputs']},'placements':placements,'application_build_verified':False,'hardware_transfer_performed':False}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'staged':str(STAGED),'checks':report['checks']},ensure_ascii=False,indent=2))

def publish():
 r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
 assert len(r['native_validation'])==len(r['ladder_counts'])
 assert all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
 assert r['native_connections'].get('missing')==0 and r['native_connections'].get('coils')==1321
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256'],'M版更新のため停止'
 assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
 with STAGED.open('rb') as src,DEST.open('xb') as dst:shutil.copyfileobj(src,dst)
 assert hashlib.sha256(DEST.read_bytes()).hexdigest()==r['output_sha256']
 print('保存完了：'+str(DEST))

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
