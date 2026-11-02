"""指定された入力5行と補助配列を除去し、Errorを既存信号への直接参照に戻す。"""
from pathlib import Path
import copy,hashlib,json,re,shutil,sys,xml.etree.ElementTree as ET,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
PREV=json.loads((BASE.parent/'cylinder-inline-20261029/verification.json').read_text(encoding='utf-8-sig'))
SRC=Path(PREV['destination']);DEST=SRC.with_name(SRC.name.replace('20261029N','20261029O'));STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'
TARGET='Error_ST7_A_Sample_M'
SOURCES=['ST7_A_Dis2_M[11]','ST7_A_Dis2_M[8]','TimerQ_In_Sen_Work_A_Pos_07','Station_A_Data[7].Work_On','TimerQ_In_Sen_NG2_Tray_B_Full']

def fields(line):return dict(x.split('=',1) for x in line[2:].rstrip('\r\n').split('\t') if '=' in x)
def declarations(t):return {fields(l)['N']:l for l in t.splitlines(keepends=True) if l.startswith('++D=')}
def dump(rows):return ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in rows)

def build():
 assert not DEST.exists(),'既存O版は上書きしません'
 with zipfile.ZipFile(SRC) as z:
  assert z.testzip() is None
  raw={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
 texts={}
 for n,b in raw.items():
  try:texts[n]=b.decode('utf-8-sig')
  except UnicodeError:pass
 rows={n:[json.loads(l) for l in t.splitlines() if l.strip()] for n,t in texts.items() if t.startswith('{"CLs"')}
 oem=ET.fromstring(next(t for n,t in texts.items() if n.endswith('.oem')))
 names={e.get('name'):next(n for n in rows if n.endswith(e.get('id')+'.xml')) for e in oem.iter('Entity') if e.get('type')=='PouBody' and e.get('subtype')=='Ladder'}
 inp,err=names['Input_入力'],names['Error_エラー処理'];changes={};new=copy.deepcopy(rows)
 assert len(rows[inp])>=5
 for i,r in enumerate(rows[inp][:5]):
  assert [(c['__type'],c.get('Var')) for c in r['CLs']]==[('LD',SOURCES[i]),('ST',f'{TARGET}[{i}]')]
 new[inp]=new[inp][5:];changes[inp]=dump(new[inp])
 replaced=0;changed_error=[]
 for i,r in enumerate(new[err]):
  touched=False
  for c in r['CLs']:
   var=c.get('Var','');m=re.fullmatch(re.escape(TARGET)+r'\[([0-4])\]',var)
   if m:
    assert c['__type']=='LD';c['Var']=SOURCES[int(m[1])];replaced+=1;touched=True
  if touched:
   changed_error.append(i)
   r['CMT']=r.get('CMT','').replace('入力側で取り込んだ判定時点の値を使用','既存信号を直接参照（補助配列なし）')
 assert replaced==9 and len(changed_error)==3
 changes[err]=dump(new[err])
 decl_names=[]
 for n,t in texts.items():
  if not t.startswith('[SLWD'):continue
  d=declarations(t)
  if TARGET in d:
   assert fields(d[TARGET])['D']=='ARRAY[0..4] OF BOOL'
   changes[n]=t.replace(d[TARGET],'',1);decl_names.append(n)
 assert len(decl_names)==3
 mode=next(n for n in decl_names if n.endswith('b530d740-9d69-41c3-974a-97c06e823eb2.xml'))
 glob=next(n for n in decl_names if n.endswith('f07dd06c-505c-431b-b9fc-098949805b4e.xml'))
 registered=[]
 for name in ('TimerQ_In_Sen_Work_A_Pos_07','TimerQ_In_Sen_NG2_Tray_B_Full'):
  assert name not in declarations(changes[mode])
  line=declarations(texts[glob])[name];assert fields(line)['G']=='VAR_GLOBAL'
  assert fields(line)['D'].upper()=='BOOL'
  line=line.replace('\tG=VAR_GLOBAL\t','\tG=VAR_EXTERNAL\t',1)
  line=line.rstrip('\r\n')
  for attribute in ('Const','RO'):
   assert fields(line).get(attribute,'0')=='0'
   if attribute not in fields(line):line+='\t'+attribute+'=0'
  changes[mode]=changes[mode].rstrip('\r\n')+'\r\n'+line.rstrip('\r\n')+'\r\n'
  registered.append({'entry':mode,'name':name,'type':'BOOL'})
 # 実変数は増設せず、既存グローバルを参照する外部宣言だけを登録。
 for n in decl_names:
  before=declarations(texts[n]);after=declarations(changes[n])
  expected=set(before)-{TARGET}
  if n==mode:expected.update(x['name'] for x in registered)
  assert set(after)==expected
  for name in set(before)&set(after):assert before[name]==after[name]
 meta=next(n for n,t in texts.items() if '<Variable ' in t and f'Name="{TARGET}"' in t)
 pattern=re.compile(r'<Variable\b(?=[^>]*\bName="'+TARGET+r'")[^>]*/>')
 changes[meta],count=pattern.subn('',texts[meta]);assert count==1;ET.fromstring(changes[meta])
 for n,t in changes.items():
  assert TARGET not in t
  raw[n]=(b'\xef\xbb\xbf' if raw[n].startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf-8')
 assert len(changes)==6
 for n,b in raw.items():assert TARGET.encode() not in b,('残存参照',n)
 # Errorの変更箇所を元の参照に戻すと元行と完全一致する。配線/命令数は不変。
 for i,(before,after) in enumerate(zip(rows[err],new[err])):
  restored=copy.deepcopy(after)
  for c in restored['CLs']:
   if c['__type']=='LD' and c.get('Var') in SOURCES and i in changed_error:c['Var']=f'{TARGET}[{SOURCES.index(c["Var"])}]'
  if 'CMT' in before:restored['CMT']=before['CMT']
  else:restored.pop('CMT',None)
  assert restored==before
 assert new[inp]==rows[inp][5:]
 with zipfile.ZipFile(STAGED,'w') as z:
  z.comment=comment
  for info in infos:z.writestr(info,raw[info.filename])
 with zipfile.ZipFile(STAGED) as z,zipfile.ZipFile(SRC) as original:
  assert z.testzip() is None and z.namelist()==original.namelist()
  assert set(n for n in z.namelist() if z.read(n)!=original.read(n))==set(changes)
  assert z.read(names['Output_出力'])==original.read(names['Output_出力'])
 report={'source':str(SRC),'destination':str(DEST),'staged':str(STAGED),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'changed_entries':list(changes),'ladder_counts':{n:len(r) for n,r in new.items()},'new_declarations':registered,'native_validation':{},'native_variables':{},'native_connections':{},'checks':{'removed_input_rungs':5,'removed_global_arrays':1,'removed_external_sample_declarations':2,'replaced_error_contacts':replaced,'existing_global_reference_registrations':2,'new_global_variables':0,'added_rungs':0,'target_remaining_references':0,'output_and_other_sections_preserved':True,'reference_timing':'Error実行時の既存信号を直接参照。前周期の補助コピーは使用しない。'},'application_build_verified':False,'hardware_transfer_performed':False}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'staged':str(STAGED),'checks':report['checks']},ensure_ascii=False,indent=2))

def publish():
 r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
 assert len(r['native_validation'])==23 and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
 assert r['native_variables'] and r['native_connections'].get('missing')==0
 assert hashlib.sha256(SRC.read_bytes()).hexdigest()==r['source_sha256']
 assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
 with STAGED.open('rb') as src,DEST.open('xb') as dst:shutil.copyfileobj(src,dst)
 print('保存完了：'+str(DEST))

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
