"""前後の全要素を比較し、番号以外を保持してD版保存・C版履歴移動する。"""
from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import hashlib,json,re,os

b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
src=Path(m['source']);dest=Path(m['output']);stage=Path(m['staged']);archive=Path(m['archive'])
assert m['native_validation']['box_section']=='TOTAL=42 PARSE_FAIL=0 MODEL_FAIL=0'
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
with ZipFile(src) as a,ZipFile(stage) as z:
 assert z.testzip() is None and a.namelist()==z.namelist()
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==[m['target']]
 al=a.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 bl=z.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 assert len(al)==len(bl)==42
 changed_rows={i for i,(x,y) in enumerate(zip(al,bl)) if x!=y}
 assert changed_rows=={13,14,15,*range(36,42)}
 old=[json.loads(l) for l in al];new=[json.loads(l) for l in bl]
 differences=[]
 def compare(before,after,path):
  assert type(before)==type(after)
  if isinstance(before,dict):
   assert list(before)==list(after)
   for k in before:compare(before[k],after[k],path+[k])
  elif isinstance(before,list):
   assert len(before)==len(after)
   for i,(x,y) in enumerate(zip(before,after)):compare(x,y,path+[i])
  else:
   match=re.fullmatch(r'BoxPacking_M\[(\d+)\]',before) if isinstance(before,str) and path[-1]=='Var' else None
   if match and 43<=int(match[1])<=49 and path!=m['terminal_coil_preserved']:
    assert after==f'BoxPacking_M[{int(match[1])-1}]';differences.append(path)
   else:assert before==after,(path,before,after)
 compare(old,new,[])
 assert len(differences)==m['changed_refs']
 coils=[int(re.fullmatch(r'BoxPacking_M\[(\d+)\]',c['Var'])[1]) for r in new for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',c.get('Var',''))]
 assert coils==list(range(1,50)) and len(set(coils))==49
 assert new[36]['CLs'][0]['Var']=='BoxPacking_M[41]'
 assert new[36]['CLs'][5]['Var']=='BoxPacking_M[42]'
 assert [c['Var'] for c in new[-1]['CLs'] if c['__type']=='ST']==['BoxPacking_M[49]']
 assert new[-1]['CLs'][0]['Var']=='BoxPacking_M[48]'

data=stage.read_bytes();assert hashlib.sha256(data).hexdigest()==m['output_sha256']
assert not dest.exists() and not archive.exists()
root=src.parent.resolve();assert src.resolve().parent==root and dest.resolve().parent==root
assert archive.parent.resolve().is_relative_to(root) and archive.resolve().parent==archive.parent.resolve()
archive.parent.mkdir(exist_ok=True)
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
with dest.open('xb') as f:f.write(data)
assert dest.read_bytes()==data
m['published']=True
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
os.rename(src,archive)
assert not src.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()==m['source_sha256']
m['archived']=True
m['independent_verification']={'new_stages':0,'rows_before':42,'rows_after':42,'changed_refs':len(differences),'coil_range':[1,49],'duplicate_coils':0,'missing_coils':0,'unmodified_rows_byte_identical':True,'updated_forward_reference_rows':[13,14,15],'non_number_fields_unchanged':True,'ST_text_unchanged':True,'other_parts_identical':m['preserved_parts'],'terminal_stage_49_preserved':True,'source_archived_byte_identical':True}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(dest),'archive':str(archive),'verification':m['independent_verification'],'output_sha256':m['output_sha256']},ensure_ascii=False))
