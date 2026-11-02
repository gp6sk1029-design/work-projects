"""指定先へ4セクションを統合し、参照時点は明示的な入力受渡しで維持する。"""
from pathlib import Path
import collections,copy,hashlib,itertools,json,re,shutil,sys,uuid,xml.etree.ElementTree as ET,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
J=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
SOURCE=Path(J['source']);DEST=SOURCE.with_name(SOURCE.name.replace('20261029L','20261029M'))
STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'
N=J['names'];T=J['texts'];R=J['rows'];PREFIX=N['HMI'].rsplit('/',1)[0]+'/'
SAMPLE='Error_ST7_A_Sample_M';WORK='HMI_Error_WorkSample'
SOURCES=['ST7_A_Dis2_M[11]','ST7_A_Dis2_M[8]','TimerQ_In_Sen_Work_A_Pos_07','Station_A_Data[7].Work_On','TimerQ_In_Sen_NG2_Tray_B_Full']

def walk(v):
 if isinstance(v,dict):
  yield v
  for x in v.values():yield from walk(x)
 elif isinstance(v,list):
  for x in v:yield from walk(x)
def fields(line):return dict(p.split('=',1) for p in line.rstrip('\r\n')[2:].split('\t') if '=' in p)
def declarations(t):return {fields(l)['N']:l for l in t.splitlines() if l.startswith('++D=')}
def field(line,key,val):
 p=re.compile(r'(?<=\t)'+re.escape(key)+'=[^\t\r\n]*')
 return p.sub(lambda m:key+'='+val,line) if p.search(line) else line+'\t'+key+'='+val
def ec_xml(values):
 root=ET.Element('ECs')
 for i,v in values.items():ET.SubElement(root,'EC',{'EK':f'[{i}]','C':v})
 return ET.tostring(root,encoding='unicode')
def decl(n,t,g,c,ec=None):
 return f'++D={t}\tN={n}\tG={g}\tCom={c}\tConst=0\tRO=0'+('\tEC='+ec_xml(ec) if ec else '')
def add_decl(text,line):
 assert fields(line)['N'] not in declarations(text)
 return text.rstrip('\r\n')+'\r\n'+line+'\r\n'
def dump(rows):return ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in rows)
def banner(row,title,purpose,target='',note=''):
 r=copy.deepcopy(row)
 lines=['# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━','# 【'+title+'】','#', '# 目的：'+purpose]
 if target:lines.append('# 対象：'+target)
 if note:lines.append('# 注意：'+note)
 lines.append('# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
 r['CMT']='\r\n'.join(lines)+('\r\n'+r['CMT'] if r.get('CMT') else '')
 return r
def capture(source,target,comment):
 return {'CLs':[{'__type':'LD','Ix':0,'Var':source},{'__type':'ST','Ix':1,'Var':target,'X':1}],
         'LRI':2,'RRI':3,'VLs':[],'CMT':comment}
def run_rung(row,values):
 graph=collections.defaultdict(list)
 for c in row['CLs']:
  on=True
  if c['__type']=='LD':on=bool(values.get(c['Var'],False))!=c.get('Not',False)
  if on:
   x,y=c.get('X',0),c.get('Y',0);graph[(x,y)].append((x+1,y))
 for v in row.get('VLs',[]):
  a=(v.get('X',0),v.get('Y',0));b=(a[0],a[1]+1);graph[a].append(b);graph[b].append(a)
 end=max([c.get('Y',0) for c in row['CLs']]+[v.get('Y',0)+1 for v in row.get('VLs',[])])
 reached={(0,y) for y in range(end+1)};todo=list(reached)
 while todo:
  for b in graph[todo.pop()]:
   if b not in reached:reached.add(b);todo.append(b)
 for c in row['CLs']:
  if c['__type']!='ST':continue
  on=(c.get('X',0),c.get('Y',0)) in reached;var=c['Var']
  if c.get('S'):values[var]=bool(values.get(var,False)) or on
  elif c.get('RS'):values[var]=bool(values.get(var,False)) and not on
  else:values[var]=on
def no_comment(r):
 v=copy.deepcopy(r);v.pop('CMT',None);return v
def aliases(a,b):return a==b or a.startswith(b+'.') or b.startswith(a+'.') or a.startswith(b+'[') or b.startswith(a+'[')

def check_other_writes():
 # 元の異常収集からInput開始までのOtherDeviceが、5サンプルを更新しないこと。
 writes=[]
 for section in ('RCON_IAI','DLEP1_GT2','FH_5552_10','CV2A_KED','HMI'):
  for index,row in enumerate(R[N[section]]):
   for c in row['CLs']:
    targets=[]
    if c['__type']=='ST':targets.append(c.get('Var',''))
    if c['__type'] in ('F','FB'):targets += [p.get('Var','') for p in c.get('Out',[]) if p.get('Var')]
    if c['__type']=='IST':targets += re.findall(r'([A-Za-z_][A-Za-z0-9_.\[\]]*)\s*:=',c.get('TXT',''))
    for target in targets:
     assert not any(aliases(target,s) for s in SOURCES),('入力取込み位置の競合',section,index,target)
     writes.append(target)
 return len(writes)

def source_state(data,previous):
 fault,gate,sensor,work,full=data;a,b=previous
 if not fault:a=b=False
 if gate and sensor!=work:a=True
 if gate and full:b=True
 return a,b

def build():
 assert not DEST.exists(),'既存M版は上書きしません'
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==J['sha256'],'L版が更新されています'
 with zipfile.ZipFile(SOURCE) as z:
  assert z.testzip() is None
  raw={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
 changes={};deleted=set();new=dict(R)
 err=N['Error_エラー処理'];hmi=N['HMI'];out=N['Output_出力'];inp=N['Input_入力']
 requests=N['HMI_Request_表示要求'];restart=N['Restart_再開処理'];collect=N['ErrorCollect_異常収集'];cylinder=N['ErrorCylinder_シリンダ異常監視']
 assert len(R[err])==56 and len(R[requests])==8 and len(R[collect])==3 and len(R[cylinder])==100
 verified_writes=check_other_writes()
 # 参照時点を保つための5入力。OtherDevice通過後・Inputのフィルタ更新前に記録。
 sampled=[capture(s,f'{SAMPLE}[{i}]',c) for i,(s,c) in enumerate(zip(SOURCES,['元異常','判定中','実ワーク','登録ワーク','満杯（既存B側）']))]
 sampled[0]=banner(sampled[0],'異常判定用入力の取込み','入力更新前のST7状態を記録する','A(左側) ST7','異常判定本体はError内。ここでは値だけを取り込む')
 new[inp]=sampled+R[inp]
 # ErrorCollectは、取り込んだ前周期の判定時点を使い、唯一の参照先の直前で処理。
 moved_collect=copy.deepcopy(R[collect])
 for row in moved_collect:
  for c in row['CLs']:
   if c.get('__type')=='LD' and c.get('Var') in SOURCES:c['Var']=f'{SAMPLE}[{SOURCES.index(c["Var"])}]'
 moved_collect[0]=banner(moved_collect[0],'ST7｜異常理由の記録','ワーク不一致・満杯の発生理由を保持する','A(左側) ST7','入力側で取り込んだ判定時点の値を使用')
 error_rows=copy.deepcopy(R[err]);st7_index=next(i for i,r in enumerate(error_rows) if r.get('CMT','').startswith('#A(左側) ST7'))
 error_rows[st7_index:st7_index]=moved_collect
 # 表示用2入力は再開によるビット解除の前に取り込み、HMIへ渡す。
 work_samples=[capture('ST1_A_Ca1_M[6]',f'{WORK}[0]','A(左側) ST1 ワーク不一致'),capture('ST5_A_Ca2_M[6]',f'{WORK}[1]','A(左側) ST5 ワーク不一致')]
 work_samples[0]=banner(work_samples[0],'表示用判定値の受渡し','再開時の解除で表示要求を見失わないようにする','ST1・ST5 ワーク不一致','表示要求の生成・番号選択はHMI内')
 error_rows += work_samples
 restarted=copy.deepcopy(R[restart]);restarted[0]=banner(restarted[0],'自動運転の再開','既存の開始・安全・異常解除条件で停止を解除する','Pause・Out_TDC_Stop','既存の条件と処理順を維持')
 error_rows += restarted
 # Error内の大区分/ST区分を共通見出しにする。
 for i,row in enumerate(error_rows):
  c=row.get('CMT','')
  if i==0:error_rows[i]=banner(row,'共通異常・非常停止','既存の非常停止条件を判定する',note='安全回路の追加・変更は行わない')
  elif c.startswith('#A(左側)検査コンベア'):error_rows[i]=banner(row,'搬送共通｜ワーク不一致','搬送時の不一致を保持し、停止とワーク情報更新を行う')
  elif c.startswith('#搬送ワーク不一致 表示要求'):error_rows[i]=banner(row,'搬送共通｜表示要求','確定した搬送異常からST別の表示要求を生成する')
  elif c.startswith(('#A(左側) ST','#B(右側) ST')):
   label=c.split('\r\n',1)[0].lstrip('#')
   error_rows[i]=banner(row,'ST別異常｜'+label,'原因別の異常保持と停止を処理する')
 new[err]=error_rows
 # 表示要求8行はHMI先頭へ。局所BOOL2つを同名グローバル化し、同じ値を共有。
 moved_requests=copy.deepcopy(R[requests])
 for row in moved_requests:
  for c in row['CLs']:
   if c.get('__type')=='LD' and c.get('Var')=='ST1_A_Ca1_M[6]':c['Var']=f'{WORK}[0]'
   elif c.get('__type')=='LD' and c.get('Var')=='ST5_A_Ca2_M[6]':c['Var']=f'{WORK}[1]'
 moved_requests[0]=banner(moved_requests[0],'表示要求の生成','FH異常・時間超過・ワーク不一致を表示要求へ変換する','ST1・ST5','再開前のワーク判定値を受け取って使用')
 hmi_rows=copy.deepcopy(R[hmi])
 for i,row in enumerate(hmi_rows):
  c=row.get('CMT','')
  if c.startswith('#シリンダ異常'):hmi_rows[i]=banner(row,'表示番号の選択｜シリンダ異常','前周期の要求から表示番号を選ぶ',note='同時要求は既存の後段優先')
  elif c.startswith('#ST別異常'):hmi_rows[i]=banner(row,'表示番号の選択｜ST別異常','ST別の異常表示要求を反映する')
  elif c.startswith('#検査コンベア異常'):hmi_rows[i]=banner(row,'表示番号の選択｜搬送共通','搬送ワーク不一致を優先表示する')
  elif c.startswith('#FH判定結果'):hmi_rows[i]=banner(row,'表示番号の選択｜FH判定','検査の判定結果を表示する')
  elif c.startswith('#FH表示要求の消費'):hmi_rows[i]=banner(row,'表示要求の解除','消費済みのFH単発要求だけを解除する')
  elif any(c.get('__type')=='IST' for c in row['CLs']) and (i==0 or not any(c.get('__type')=='IST' for c in hmi_rows[i-1]['CLs'])):
   hmi_rows[i]=banner(row,'表示文字の変換','既存の日本語・英語の文面へ変換する',note='番号と文面の既存対応は今回変更しない')
 new[hmi]=moved_requests+hmi_rows
 # 同じIO内で、Output→ErrorCylinderの連続実行をそのまま1セクションへ結合。
 out_rows=copy.deepcopy(R[out]);out_rows[0]=banner(out_rows[0],'出力制御・動作完了','運転条件から出力と完了信号を処理する')
 cyl_rows=copy.deepcopy(R[cylinder]);cyl_rows[0]=banner(cyl_rows[0],'シリンダ異常監視','動作要求とセンサ状態の不一致を時間監視する','A側・B側・共通シリンダ','監視条件・時間・保持方式は変更しない')
 new[out]=out_rows+cyl_rows
 for n in (err,hmi,out,inp):changes[n]=dump(new[n])

 # 宣言の移行。保持/割付/定数/型を勝手に変えない。
 suffixes={'global':'f07dd06c-505c-431b-b9fc-098949805b4e.xml','mode':'b530d740-9d69-41c3-974a-97c06e823eb2.xml','other':'a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml','io':'9576fedf-9472-4ce6-b9ed-6eda5b4f0514.xml','meta':'20a6b651-4c34-401a-965e-db3e18414d5c.xml'}
 varnames={k:next(n for n in T if n.endswith(v)) for k,v in suffixes.items()}
 globals_added={SAMPLE:decl(SAMPLE,'ARRAY[0..4] OF BOOL','VAR_GLOBAL','#A(左側) ST7 異常判定の入力取込み',{0:'元異常',1:'判定中',2:'実ワーク',3:'登録ワーク',4:'満杯（既存B側）'}),
                WORK:decl(WORK,'ARRAY[0..1] OF BOOL','VAR_GLOBAL','#HMI 再開前のワーク不一致',{0:'A(左側) ST1',1:'A(左側) ST5'})}
 mode_lines=T[varnames['mode']].splitlines(keepends=True)
 timeout_names=('Error_ST1_A_Timeout','Error_ST5_A_Timeout')
 for name in timeout_names:
  line=next(l for l in mode_lines if l.startswith('++D=') and fields(l)['N']==name)
  p=fields(line);assert p['G']=='VAR' and p['D']=='BOOL' and p.get('Const')==p.get('RO')=='0'
  globals_added[name]=field(line.rstrip('\r\n'),'G','VAR_GLOBAL')
  mode_lines.remove(line)
 changes[varnames['mode']]=''.join(mode_lines)
 for name,line in globals_added.items():
  changes[varnames['global']]=add_decl(changes.get(varnames['global'],T[varnames['global']]),line)
  scopes=['mode']+(['io'] if name==SAMPLE else ['other'])
  for scope in scopes:
   target=varnames[scope]
   changes[target]=add_decl(changes.get(target,T[target]),field(line,'G','VAR_EXTERNAL'))
 meta=T[varnames['meta']];old_meta={e.get('Name'):e for e in ET.fromstring(meta).iter('Variable')};items=[]
 for name,line in globals_added.items():
  assert name not in old_meta
  p=fields(line);element=copy.deepcopy(old_meta['Error_M'] if p['D'].startswith('ARRAY') else next(e for e in old_meta.values() if e.get('DataTypeName')=='Boolean' and e.get('Group')=='VAR_GLOBAL'))
  datatype={'ARRAY[0..4] OF BOOL':'Boolean(4)','ARRAY[0..1] OF BOOL':'Boolean(1)','BOOL':'Boolean'}[p['D']]
  for k,v in {'Name':name,'Address':'new_Controller_0.'+name,'DataTypeName':datatype,'Id':str(uuid.uuid4()),'Comment':p.get('Com',''),'IsConstant':'false','IsReadOnly':'false','IsControllerVariable':'false','IsReadOnlyNetwork':'false','NetworkPublication':'NoPublication','Retained':'false','InitialValue':''}.items():element.set(k,v)
  element.tail=None;items.append(ET.tostring(element,encoding='unicode'))
 marker='  </VariableGroup>';assert marker in meta
 changes[varnames['meta']]=meta.replace(marker,''.join('    '+x+'\r\r\n' for x in items)+marker,1)

 # 統合済み4セクションの実体・ツリーだけをコピー内から取り除く。
 oem=T[J['oem']]
 def span(text,identity):
  m=re.search(r'<Entity\b[^>]*\bid="'+re.escape(identity)+'"[^>]*>',text);assert m
  depth=0
  for tag in re.finditer(r'</?Entity\b[^>]*>',text[m.start():]):
   if tag[0].startswith('</'):depth-=1
   elif not tag[0].endswith('/>'):depth+=1
   if depth==0:return m.start(),m.start()+tag.end()
  raise AssertionError(identity)
 removed_identities=[]
 for n in (requests,restart,collect,cylinder):
  identity=n.rsplit('/',1)[1][:-4];start,end=span(oem,identity);e=ET.fromstring(oem[start:end]);oem=oem[:start]+oem[end:]
  for ent in e.iter('Entity'):
   removed_identities += [ent.get(k) for k in ('id','trackingId') if ent.get(k)]
   for ext in ('.xml','.dat','.BookmarkGroup'):
    filename=PREFIX+ent.get('id')+ext
    if filename in raw:deleted.add(filename)
  del new[n]
 changes[J['oem']]=oem
 # 統合済みセクションを指す古いビルド照合キャッシュだけを除去する。
 verifier_name=next(n for n in T if n.endswith('.NexBuildVerifierGroup'))
 verifier=T[verifier_name];cache_removed=0
 for identity in removed_identities:
  pattern=re.compile(r'<(?P<tag>[A-Za-z_][\w.-]*:KeyValueOfguid[^\s>]*)><[A-Za-z_][\w.-]*:Key>'+re.escape(identity)+r'</[A-Za-z_][\w.-]*:Key>.*?</(?P=tag)>',re.S)
  verifier,count=pattern.subn('',verifier);cache_removed+=count
 if verifier!=T[verifier_name]:
  ET.fromstring(verifier)
  assert not any(identity in verifier or identity.replace('-','') in verifier for identity in removed_identities)
  changes[verifier_name]=verifier
 checks=verify(new,globals_added,varnames,changes,sampled,work_samples,verified_writes)
 checks['obsolete_section_cache_records_removed']=cache_removed
 for n,t in changes.items():raw[n]=(b'\xef\xbb\xbf' if raw[n].startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf-8')
 with zipfile.ZipFile(STAGED,'w') as z:
  z.comment=comment
  for info in infos:
   if info.filename not in deleted:z.writestr(info,raw[info.filename])
 with zipfile.ZipFile(STAGED) as z,zipfile.ZipFile(SOURCE) as original:
  assert z.testzip() is None
  assert set(z.namelist())==set(original.namelist())-deleted
  for n in z.namelist():
   if n not in changes:assert z.read(n)==original.read(n)
 report={'source':str(SOURCE),'staged':str(STAGED),'destination':str(DEST),'source_sha256':J['sha256'],
         'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'changed_entries':list(changes),'removed_entries':sorted(deleted),
         'moves':{'ErrorCylinder_シリンダ異常監視':'Output_出力','HMI_Request_表示要求':'HMI','ErrorCollect_異常収集':'Error_エラー処理','Restart_再開処理':'Error_エラー処理'},
         'checks':checks,'ladder_counts':{n:len(rr) for n,rr in new.items()},
         'new_declarations':[{'entry':varnames[scope],'name':name,'type':fields(line)['D']} for name,line in globals_added.items() for scope in (['global','mode','io'] if name==SAMPLE else ['global','mode','other'])],
         'native_validation':{},'native_variables':{},'native_connections':{},'application_build_verified':False,'hardware_transfer_performed':False}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'staged':str(STAGED),'sections':len(new),'rungs':sum(map(len,new.values())),'checks':checks},ensure_ascii=False,indent=2))

def verify(new,added,varnames,changes,sampled,work_samples,verified_writes):
 # 原処理はコメントと明示した入力変数置換以外を完全保持。
 old_collect=R[N['ErrorCollect_異常収集']]
 err=new[N['Error_エラー処理']];selected=[r for r in err if any(c.get('__type')=='ST' and c.get('Var','').startswith('Error_ST7_A_Source_M') for c in r['CLs'])]
 assert len(selected)==3
 for old,new_row in zip(old_collect,selected):
  restored=copy.deepcopy(new_row)
  for c in restored['CLs']:
   if c.get('Var','').startswith(SAMPLE+'['):c['Var']=SOURCES[int(c['Var'].split('[')[1].rstrip(']'))]
  assert no_comment(old)==no_comment(restored)
 hmi_rows=new[N['HMI']]
 for old,after in zip(R[N['HMI_Request_表示要求']],hmi_rows[:8]):
  restored=copy.deepcopy(after)
  for c in restored['CLs']:
   if c.get('Var')==WORK+'[0]':c['Var']='ST1_A_Ca1_M[6]'
   elif c.get('Var')==WORK+'[1]':c['Var']='ST5_A_Ca2_M[6]'
  assert no_comment(old)==no_comment(restored)
 assert [no_comment(r) for r in hmi_rows[8:]]==[no_comment(r) for r in R[N['HMI']]]
 assert no_comment(err[-1])==no_comment(R[N['Restart_再開処理']][0])
 assert [no_comment(r) for r in new[N['Output_出力']]]==[no_comment(r) for r in R[N['Output_出力']]+R[N['ErrorCylinder_シリンダ異常監視']]]
 # 実際の移動前/後ラダーを実行し、入力取込み後の更新で原因が変わらないことを検査。
 source_cases=0
 for data in itertools.product((False,True),repeat=5):
  for prior in itertools.product((False,True),repeat=2):
   old_values=dict(zip(SOURCES,data));old_values.update({'Error_ST7_A_Source_M[3]':prior[0],'Error_ST7_A_Source_M[4]':prior[1]})
   for row in old_collect:run_rung(row,old_values)
   expected=(old_values['Error_ST7_A_Source_M[3]'],old_values['Error_ST7_A_Source_M[4]'])
   assert expected==source_state(data,prior)
   for refreshed in itertools.product((False,True),repeat=5):
    new_values=dict(zip(SOURCES,data));new_values.update({'Error_ST7_A_Source_M[3]':prior[0],'Error_ST7_A_Source_M[4]':prior[1]})
    for row in sampled:run_rung(row,new_values)
    new_values.update(zip(SOURCES,refreshed))
    for row in selected:run_rung(row,new_values)
    actual=(new_values['Error_ST7_A_Source_M[3]'],new_values['Error_ST7_A_Source_M[4]'])
    assert actual==expected,(data,refreshed,prior)
    source_cases+=1
 display_cases=0
 triggers=[next(c['Var'] for c in row['CLs'] if c['__type']=='LD') for row in R[N['HMI_Request_表示要求']]]
 outputs=[next(c['Var'] for c in row['CLs'] if c['__type']=='ST') for row in R[N['HMI_Request_表示要求']]]
 for values in itertools.product((False,True),repeat=8):
  for after_reset in itertools.product((False,True),repeat=2):
   original=dict(zip(triggers,values));modified=dict(original)
   for row in R[N['HMI_Request_表示要求']]:run_rung(row,original)
   for row in work_samples:run_rung(row,modified)
   modified.update({'ST1_A_Ca1_M[6]':after_reset[0],'ST5_A_Ca2_M[6]':after_reset[1]})
   for row in hmi_rows[:8]:run_rung(row,modified)
   assert [original[o] for o in outputs]==[modified[o] for o in outputs]
   display_cases+=1
 # 全ST7 Source参照はErrorに集約。通常動作や機器データ更新はその他でそのまま。
 for n,rr in new.items():
  if n==N['Error_エラー処理']:continue
  assert not any(node.get('Var','').startswith('Error_ST7_A_Source_M') for r in rr for node in walk(r))
 # 宣言は2つの元局所BOOLのglobal化と、2つの受渡し配列だけ。
 at_count=0
 for n,t in T.items():
  if not t.startswith('[SLWD'):continue
  a,b=declarations(t),declarations(changes.get(n,t))
  assert len(b)==len({x.lower() for x in b})
  for name,line in a.items():
   if n==varnames['mode'] and name in ('Error_ST1_A_Timeout','Error_ST5_A_Timeout'):
    assert fields(b[name])['G']=='VAR_EXTERNAL' and fields(b[name])['D']==fields(line)['D']
   else:assert line==b[name],(n,name)
   at_count+=bool(fields(line).get('AT'))
  for name,line in b.items():
   if name in added:
    p=fields(line);assert p['Const']==p['RO']=='0' and not p.get('AT')
 # ツリーの4セクションがなくなり、指定先だけになる。
 oem=ET.fromstring(changes[J['oem']]);section_names=[e.get('name') for e in oem.iter('Entity') if e.get('type')=='PouBody']
 assert not any(s in section_names for s in ('ErrorCollect_異常収集','ErrorCylinder_シリンダ異常監視','HMI_Request_表示要求','Restart_再開処理'))
 changed_rows=set(changes)&set(R)
 assert changed_rows=={N[s] for s in ('Input_入力','Output_出力','Error_エラー処理','HMI')}
 assert all(new[n]==rr for n,rr in R.items() if n not in changed_rows and n in new)
 return {'snapshot_phase_cases':source_cases,'display_handoff_cases':display_cases,'other_device_write_targets_checked':verified_writes,
         'io_output_flat_instruction_order_preserved':True,'old_rung_geometry_and_up_ids_preserved':True,
         'old_hmi_priority_and_language_unchanged':True,'physical_io_assignments_preserved':at_count,
         'task_program_order_unchanged':True,'new_snapshot_rungs':len(sampled)+len(work_samples),'major_headers_standardized':True}

def publish():
 r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
 assert r['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
 assert r['native_variables'] and r['native_connections'].get('missing')==0
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256']
 assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
 with STAGED.open('rb') as src,DEST.open('xb') as dst:shutil.copyfileobj(src,dst)
 print('保存完了：'+str(DEST))

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
