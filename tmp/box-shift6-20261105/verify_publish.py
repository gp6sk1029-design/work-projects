"""生成物を独立に読み、逆置換で元回路との一致を確認して指定先へ保存する。"""
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
import json,hashlib,re

b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
src=Path(m['source']);stage=Path(m['staged']);dest=Path(m['output'])
assert m['native_validation']['box_section']=='TOTAL=41 PARSE_FAIL=0 MODEL_FAIL=0'
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
with ZipFile(src) as a,ZipFile(stage) as z:
 assert z.testzip() is None and a.namelist()==z.namelist() and len(z.namelist())==212
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==[m['target']]
 al=a.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 bl=z.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 assert len(al)==len(bl)==41 and al[:2]==bl[:2]
 old=[json.loads(l) for l in al];new=[json.loads(l) for l in bl]
 restored=deepcopy(new);count=[0]
 def reverse(v):
  if isinstance(v,dict):
   for k,value in v.items():
    if k=='Var' and isinstance(value,str):
     match=re.fullmatch(r'BoxPacking_M\[(\d+)\]',value)
     if match and int(match[1])>=7:
      v[k]=f'BoxPacking_M[{int(match[1])-1}]';count[0]+=1
     elif match:assert int(match[1])<=5,'後続工程に旧[6]が残っている'
    else:reverse(value)
  elif isinstance(v,list):
   for value in v:reverse(value)
 for row in restored[2:]:reverse(row)
 assert restored==old,'番号の繰下げ以外に変更あり'
 assert count[0]==m['changed_refs']==127
 coilnumbers=[int(re.fullmatch(r'BoxPacking_M\[(\d+)\]',c['Var'])[1]) for r in new for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',c.get('Var',''))]
 assert coilnumbers==list(range(1,49)) and len(coilnumbers)==len(set(coilnumbers))
 assert [c['Var'] for c in new[1]['CLs'] if c['__type']=='ST' and c.get('Var','').startswith('BoxPacking_M[')]==[f'BoxPacking_M[{n}]' for n in range(2,7)]
 assert all(c['Var']=='BoxPacking_M[7]' for c in new[2]['CLs'] if c['__type']=='ST' and c.get('Var','').startswith('BoxPacking_M['))

data=stage.read_bytes();assert hashlib.sha256(data).hexdigest()==m['output_sha256']
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
assert not dest.exists()
with dest.open('xb') as f:f.write(data)
assert dest.read_bytes()==data
m['published']=True
m['independent_verification']={'reverse_mapping_matches_source':True,'changed_refs':127,'coil_indices':list(range(1,49)),'duplicates':0,'gaps':0,'first_two_rows_byte_identical':True,'other_parts_identical':211,'all_ST_text_unchanged':True,'source_unchanged':True,'destination_matches_verified_file':True}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(dest),'changed_refs':127,'coil_range':'1～48','duplicates':0,'gaps':0,'output_sha256':m['output_sha256'],'original_unchanged':True},ensure_ascii=False))
