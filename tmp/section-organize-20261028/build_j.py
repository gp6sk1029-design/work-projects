"""最新I版の補助ラダーを同じPOU内の役割別セクションへ整理する。"""
from pathlib import Path
import collections,copy,hashlib,json,re,shutil,sys,uuid,xml.etree.ElementTree as ET,zipfile
import dependencies as d

sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
J=d.J;SOURCE=Path(J['source']);DEST=SOURCE.with_name(SOURCE.name.replace('20261029I','20261029J'))
STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'
N=J['names'];T=J['texts'];R=J['ladders'];PREFIX=N['Section0'].rsplit('/',1)[0]+'/'

def gid():return str(uuid.uuid4())
def dump(rows):return ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in rows)
def without_comment(row):
 r=copy.deepcopy(row);r.pop('CMT',None);return r
def title(rows,text):
 rr=copy.deepcopy(rows);rr[0]['CMT']=text+('\r\n'+rr[0]['CMT'] if rr[0].get('CMT') else '');return rr

def entity_span(text,entity_id):
 match=re.search(r'<Entity\b[^>]*\bid="'+re.escape(entity_id)+r'"[^>]*>',text)
 assert match,entity_id
 depth=0
 for tag in re.finditer(r'</?Entity\b[^>]*>',text[match.start():]):
  if tag[0].startswith('</'):depth-=1
  elif not tag[0].endswith('/>'):depth+=1
  if depth==0:return match.start(),match.start()+tag.end()
 raise AssertionError(entity_id)

def build():
 assert not DEST.exists(),'既存J版は上書きしません'
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==J['sha256'],'調査後にI版が更新されています'
 with zipfile.ZipFile(SOURCE) as z:
  assert z.testzip() is None
  raw={n:z.read(n) for n in z.namelist()};infos=z.infolist();archive_comment=z.comment
 changes={};added={};new=dict(R);audits=[]
 st7=N['ST7_A_Dis2_左SF排出'];empty=N['Section0'];err=N['Error_エラー処理'];out=N['Output_出力']
 assert R[empty]==[{'CLs':[],'RRI':1,'VLs':[]}]
 source_rows=R[st7][9:12]
 assert len(source_rows)==3 and all(any(c.get('Var','').startswith('Error_ST7_A_Source_M') and c['__type']=='ST' for c in r['CLs']) for r in source_rows)
 # ST7の後半を越えても、収集する値や収集結果に介在する書込みはない。
 st7_pairs=0
 for i in (9,10,11):
  for k in range(12,len(R[st7])):
   assert not d.conflicts(R[st7][i],R[st7][k]),('ST7移動競合',i,k)
   st7_pairs+=1
 new[st7]=R[st7][:9]+R[st7][12:]
 new[empty]=source_rows
 old_lines=T[st7].splitlines(keepends=True)
 changes[st7]=''.join(old_lines[:9]+old_lines[12:])
 changes[empty]=dump(source_rows)
 audits.append({'source':'ST7_A_Dis2_左SF排出','old_rows':[9,10,11],'destination':'ErrorCollect_異常収集','classification':'異常理由の記録/解除','reason':'ST7末尾まで読書き競合なし。同じMovements内・IO更新前で収集する'})

 # 出力の監視行は、全ての制御行より後へ移してよいことを先に照合する。
 diagnostic_indices=[i for i,r in enumerate(R[out]) if d.diag(r)]
 assert len(diagnostic_indices)==100
 diagnostic_set=set(diagnostic_indices);io_pairs=0
 for i in diagnostic_indices:
  for k in range(i+1,len(R[out])):
   if k in diagnostic_set:continue
   assert not d.conflicts(R[out][i],R[out][k]),('出力監視移動競合',i,k)
   io_pairs+=1
 diagnostic_rows=[R[out][i] for i in diagnostic_indices]
 assert all(not any(c.get('__type')=='IST' for c in r['CLs']) for r in R[out])
 new[out]=[r for i,r in enumerate(R[out]) if i not in diagnostic_set]
 out_lines=T[out].splitlines(keepends=True)
 changes[out]=''.join(l for i,l in enumerate(out_lines) if i not in diagnostic_set)

 # Error内の表示要求8行を独立。ただし前後の実行順を変えない。
 assert len(R[err])==58
 capture=R[err][49:57];restart=R[err][57:]
 assert len(capture)==8 and len(restart)==1
 assert all(len([c for c in r['CLs'] if c['__type']=='ST'])==1 and any(c.get('Var','').startswith('HMI_Message_Request') for c in r['CLs']) for r in capture)
 new[err]=R[err][:49]
 changes[err]=''.join(T[err].splitlines(keepends=True)[:49])

 oem=T[J['oem_name']]
 empty_id=empty.rsplit('/',1)[1][:-4]
 a,b=entity_span(oem,empty_id);template=oem[a:b]
 root_template=ET.fromstring(template)
 template_holder=next(e for e in root_template.iter('Entity') if e.get('type')=='PouBodySourceHolder')
 template_holder_text=T[PREFIX+template_holder.get('id')+'.xml']
 template_tracking=root_template.get('trackingId')
 original_oem=ET.fromstring(oem)
 programs={e.get('name'):e for e in original_oem.iter('Entity') if e.get('type')=='Program'}
 # 空のSection0を専用収集へ転用する。元のST7の直後なので他プログラムへ移すより遅延がない。
 renamed=re.sub(r'\b(name|DN)="Section0"',lambda m:m[1]+'="ErrorCollect_異常収集"',template,count=2)
 assert renamed!=template
 oem=oem[:a]+renamed+oem[b:]
 old_holder=PREFIX+template_holder.get('id')+'.xml'
 changes[old_holder]=template_holder_text.replace('Section0_0','ErrorCollect_異常収集_0')
 created=[]

 def make_section(name,program_name,rows):
  entity=copy.deepcopy(root_template);mapping={}
  for e in entity.iter('Entity'):
   for key in ('id','trackingId'):
    value=e.get(key)
    if value:mapping.setdefault(value,gid());e.set(key,mapping[value])
  entity.set('name',name);entity.set('DN',name)
  section_id=entity.get('id');section_tracking=entity.get('trackingId')
  holder=next(e for e in entity.iter('Entity') if e.get('type')=='PouBodySourceHolder')
  program_tracking=programs[program_name].get('trackingId')
  cache=template_holder_text.replace(J['programs']['Movements_動作']['id'],'@未使用@')
  # ソースホルダは未コンパイルの空セクション形式。既存の実行プログラム設定は変更しない。
  cache=template_holder_text.replace(programs['Movements_動作'].get('trackingId'),program_tracking)
  cache=cache.replace(template_tracking.replace('-',''),section_tracking.replace('-','')).replace('Section0_0',name+'_0')
  # 元の空キャッシュのリンク位置を新規セクションの初期状態へ戻す。
  cache=cache.replace('Offset="9"','Offset="0"')
  filename=PREFIX+section_id+'.xml'
  added[filename]=dump(rows).encode('utf-8-sig')
  added[PREFIX+section_id+'.BookmarkGroup']=raw[PREFIX+empty_id+'.BookmarkGroup']
  added[PREFIX+holder.get('id')+'.xml']=cache.encode('utf-8-sig')
  new[filename]=rows
  created.append({'name':name,'program':program_name,'id':section_id,'rows':len(rows),'source':filename})
  return ET.tostring(entity,encoding='unicode')

 monitor_rows=title(diagnostic_rows,'#シリンダ異常監視\r\n元の監視条件・時間を維持')
 monitor_entity=make_section('ErrorCylinder_シリンダ異常監視','IO_入出力',monitor_rows)
 x,y=entity_span(oem,out.rsplit('/',1)[1][:-4]);oem=oem[:y]+'\r\n'+monitor_entity+oem[y:]
 capture_rows=title(capture,'#HMI表示要求の収集\r\n実行順維持のため、異常判定後・再開処理前')
 capture_entity=make_section('HMI_Request_表示要求','ModeManagement_モード管理',capture_rows)
 restart_entity=make_section('Restart_再開処理','ModeManagement_モード管理',restart)
 x,y=entity_span(oem,err.rsplit('/',1)[1][:-4]);oem=oem[:y]+'\r\n'+capture_entity+'\r\n'+restart_entity+oem[y:]
 changes[J['oem_name']]=oem
 audits.extend([
  {'source':'Output_出力','old_rows':diagnostic_indices,'destination':'ErrorCylinder_シリンダ異常監視','classification':'時間監視/異常保持/表示要求','reason':'後段の出力制御と読書き競合なし。同じIO内の末尾へ移動'},
  {'source':'Error_エラー処理','old_rows':list(range(49,57)),'destination':'HMI_Request_表示要求','classification':'表示要求のみ','reason':'元の前後関係をそのまま維持'},
  {'source':'Error_エラー処理','old_rows':[57],'destination':'Restart_再開処理','classification':'再開/停止解除','reason':'表示要求収集の後という元の順序を維持'},
 ])

 # 新規の変数や命令を作らず、移動前後の命令多重集合を全て照合する。
 before=collections.Counter(json.dumps(without_comment(r),sort_keys=True) for rr in R.values() for r in rr if r['CLs'])
 after=collections.Counter(json.dumps(without_comment(r),sort_keys=True) for rr in new.values() for r in rr if r['CLs'])
 assert before==after,'移動以外の命令差分'
 # Mode内はセクションを分けただけで1命令も並替えない。
 mode_order=[x['source'] for x in created if x['program']=='ModeManagement_モード管理']
 assert [without_comment(r) for r in new[err]+new[mode_order[0]]+new[mode_order[1]]]==[without_comment(r) for r in R[err]]
 assert new[st7]+new[empty]!=R[st7] # 意図した収集だけが末尾へ移る
 assert new[st7][:9]==R[st7][:9] and new[st7][9:]==R[st7][12:] and new[empty]==R[st7][9:12]
 parsed=ET.fromstring(oem);all_entities=list(parsed.iter('Entity'))
 assert len({e.get('id') for e in all_entities})==len(all_entities)
 for e in all_entities:
  if e.get('type')=='Program':
   actual=[c.get('name') for c in e.find('ChildEntities') if c.get('type')=='PouBody']
   if e.get('name')=='ModeManagement_モード管理':assert actual[-3:]==['Error_エラー処理','HMI_Request_表示要求','Restart_再開処理']
   if e.get('name')=='Movements_動作':assert actual[-2:]==['ST7_A_Dis2_左SF排出','ErrorCollect_異常収集']
   if e.get('name')=='IO_入出力':assert actual==['Input_入力','Output_出力','ErrorCylinder_シリンダ異常監視']
 assert all(n not in changes for n in T if T[n].startswith('[SLWD')),'変数宣言の意図しない変更'
 for n,t in changes.items():raw[n]=(b'\xef\xbb\xbf' if raw[n].startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf-8')
 assert not set(added)&set(raw)
 with zipfile.ZipFile(STAGED,'w') as z:
  z.comment=archive_comment
  for info in infos:z.writestr(info,raw[info.filename])
  template_info=next(i for i in infos if i.filename==empty)
  for n,data in added.items():
   info=copy.copy(template_info);info.filename=n;z.writestr(info,data)
 with zipfile.ZipFile(STAGED) as z,zipfile.ZipFile(SOURCE) as old:
  assert z.testzip() is None
  for n in old.namelist():
   if n not in changes:assert z.read(n)==old.read(n),n
  for e in all_entities:
   if e.get('type') in ('PouBody','PouBodySourceHolder'):
    filename=PREFIX+e.get('id')+'.xml'
    assert filename in z.namelist(),('実体なし',filename)
 audits.extend([
  {'source':s,'classification':'動作の成立条件/ワーク情報/機器通信','destination':'現状維持','reason':'進行判定やデータ更新と同じ行であり、補助表示だけの独立行ではない'}
  for s in N if s not in ('ST7_A_Dis2_左SF排出','Section0','Output_出力','Error_エラー処理','HMI')])
 report={'source':str(SOURCE),'staged':str(STAGED),'destination':str(DEST),'source_sha256':J['sha256'],
         'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'changed_entries':list(changes),'added_entries':list(added),
         'section_audit':audits,'new_sections':created,'reused_blank_section':'ErrorCollect_異常収集',
         'checks':{'st7_commutation_pairs':st7_pairs,'output_commutation_pairs':io_pairs,'read_write_conflicts':0,
                   'all_nonempty_rungs_and_existing_instruction_ids_preserved':True,'mode_instruction_order_preserved':True,
                   'all_variable_declarations_io_and_task_settings_preserved':True,'hmi_communication_section_position_preserved':True,
                   'only_unused_blank_rung_removed':True,'user_updated_i_used':True},
         'ladder_counts':{n:len(rr) for n,rr in new.items()},'native_validation':{},'application_build_verified':False,
         'hardware_transfer_performed':False}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'staged':str(STAGED),'sections':len(new),'rungs':sum(map(len,new.values())), 'new_sections':created,'checks':report['checks']},ensure_ascii=False,indent=2))

def publish():
 r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
 assert r['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256']
 assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
 with STAGED.open('rb') as src,DEST.open('xb') as dst:shutil.copyfileobj(src,dst)
 print('保存完了：'+str(DEST))

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
