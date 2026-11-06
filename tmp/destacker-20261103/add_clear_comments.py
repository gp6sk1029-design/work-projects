"""C版の回路・宣言を保持して行コメントと変数要素コメントだけをD版へ反映する。"""
from pathlib import Path
from copy import copy,deepcopy
from lxml import etree as E
import zipfile,json,hashlib,io,re,csv,sys,time
from comment_plan import DESTACKER_ROWS,OUTPUT_ROWS,RCON_ROWS,VARIABLES
sys.stdout.reconfigure(encoding='utf-8')
start=time.monotonic();base=Path(__file__).parent
inspection=json.loads((base/'コメント追加前調査.json').read_text(encoding='utf-8'))
source=Path(inspection['source']);raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()==inspection['sha256'],'C版が外部更新されたため停止'
dest=source.with_name(source.name.replace('20261103C.smc2','20261103D.smc2'))
assert dest!=source and not dest.exists(),'D版の保存先が使用済み'
plans={'Destacker_段バラシ':DESTACKER_ROWS,'Output_出力':OUTPUT_ROWS,'RCON_IAI':RCON_ROWS}
logs=[];changed=[];covered={};rowchanges={};patches={}
def mask_rows(rows):return [{k:v for k,v in row.items() if k!='CMT'} for row in rows]
def fields_without_comments(line):return [p for p in line.split('\t') if not p.startswith(('Com=','EC='))]
with zipfile.ZipFile(io.BytesIO(raw)) as zin:
 assert zin.testzip() is None
 for section,plan in plans.items():
  part=inspection['sections'][section];original=zin.read(part)
  text=original.decode('utf-8-sig');lines=text.splitlines(keepends=True)
  before=[json.loads(l) for l in lines];after=deepcopy(before);rowchanges[section]=[]
  for i,comment in plan.items():
   old=after[i].get('CMT','')
   if old!=comment:
    after[i]['CMT']=comment;rowchanges[section].append(i)
    logs.append({'part':part,'kind':'行コメント','name':section,'index':i,'old':old,'new':comment})
  assert mask_rows(before)==mask_rows(after),'回路条件または構造の変更'
  output=[]
  for a,c,line in zip(before,after,lines):
   ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
   output.append(line if a==c else json.dumps(c,ensure_ascii=False,separators=(',',':'))+ending)
  patches[part]=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(output).encode('utf-8')
 for item in zin.infolist():
  if not item.filename.endswith('.xml'):continue
  original=zin.read(item.filename)
  try:text=original.decode('utf-8-sig')
  except UnicodeError:continue
  if not text.startswith('[SLWD'):continue
  ls=text.splitlines(keepends=True);result=[];modified=False
  for line in ls:
   ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
   body=line[:-len(ending)] if ending else line
   parts=body.split('\t');name=next((p[2:] for p in parts if p.startswith('N=')),None)
   if name not in VARIABLES:result.append(line);continue
   plan=VARIABLES[name];covered.setdefault(name,[]).append(item.filename)
   if 'Com' in plan:
    positions=[i for i,p in enumerate(parts) if p.startswith('Com=')];assert len(positions)<=1
    old=parts[positions[0]][4:] if positions else ''
    new=plan['Com'];assert '\t' not in new and '\n' not in new
    if old!=new:
     if positions:parts[positions[0]]='Com='+new
     else:parts.append('Com='+new)
     logs.append({'part':item.filename,'kind':'変数コメント','name':name,'index':'','old':old,'new':new})
   if 'EC' in plan:
    positions=[i for i,p in enumerate(parts) if p.startswith('EC=')];assert len(positions)<=1
    ec=E.fromstring(parts[positions[0]][3:].encode('utf-8')) if positions else E.Element('ECs')
    assert ec.tag=='ECs'
    bound=re.search(r'ARRAY\[(\d+)\.\.(\d+)\]',body,re.I);assert bound,(name,'配列宣言がない')
    for index,new in plan['EC'].items():
     assert int(bound[1])<=index<=int(bound[2])
     nodes=[e for e in ec if e.get('EK')==f'[{index}]'];assert len(nodes)<=1
     old=nodes[0].get('C','') if nodes else ''
     if old!=new:
      if nodes:nodes[0].set('C',new)
      else:E.SubElement(ec,'EC',EK=f'[{index}]',C=new)
      logs.append({'part':item.filename,'kind':'配列要素コメント','name':name,'index':index,'old':old,'new':new})
    value='EC='+E.tostring(ec,encoding='unicode')
    if positions:parts[positions[0]]=value
    else:parts.append(value)
   newbody='\t'.join(parts)
   assert fields_without_comments(body)==fields_without_comments(newbody),'型・割付・保持設定などの変更'
   result.append(newbody+ending);modified|=newbody!=body
  if modified:
   patches[item.filename]=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(result).encode('utf-8')
 assert set(covered)==set(VARIABLES),'対象変数の宣言が見つからない'
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w') as zout:
  zout.comment=zin.comment
  for item in zin.infolist():
   data=patches.get(item.filename,zin.read(item.filename))
   if data!=zin.read(item.filename):changed.append(item.filename)
   zout.writestr(copy(item),data)
 result=buf.getvalue()
 with zipfile.ZipFile(io.BytesIO(result)) as z:
  assert z.testzip() is None and z.namelist()==zin.namelist()
  for part in z.namelist():
   if part not in changed:assert z.read(part)==zin.read(part)
  for section in plans:
   part=inspection['sections'][section]
   a=[json.loads(l) for l in zin.read(part).decode('utf-8-sig').splitlines()]
   c=[json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines()]
   assert mask_rows(a)==mask_rows(c)
 assert source.read_bytes()==raw,'作業中のC版更新を検出'
 with dest.open('xb') as f:f.write(result)
 assert dest.read_bytes()==result
 count={kind:sum(x['kind']==kind for x in logs) for kind in ['行コメント','変数コメント','配列要素コメント']}
 report={'source':str(source),'output':str(dest),'source_sha256':inspection['sha256'],'output_sha256':hashlib.sha256(result).hexdigest(),'changed_parts':changed,'preserved_parts':len(zin.namelist())-len(changed),'counts':count,'row_comments_by_section':{k:len(v) for k,v in rowchanges.items()},'distinct_variable_names':len(covered),'distinct_array_elements':sum(len(v.get('EC',{})) for v in VARIABLES.values()),'logic_and_definitions_unchanged':True,'C_original_unchanged':True,'ZIP_CRC':'正常','native_Sysmac_read_and_build':'未実施','seconds':round(time.monotonic()-start,3),'covered':covered}
 (base/'D版コメント追加検証.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 with (base/'D版コメント変更一覧.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['part','kind','name','index','old','new']);w.writeheader();w.writerows(logs)
 print(json.dumps({k:v for k,v in report.items() if k!='covered'},ensure_ascii=False))
