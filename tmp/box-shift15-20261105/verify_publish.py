"""差分を独立監査し、C版を保存してから旧B版だけを履歴へ移す。"""
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
import hashlib,json,re,os

b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
src=Path(m['source']);stage=Path(m['staged']);dest=Path(m['output']);archive=Path(m['archive'])
assert m['native_validation']['box_section']=='TOTAL=42 PARSE_FAIL=0 MODEL_FAIL=0'
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
with ZipFile(src) as a,ZipFile(stage) as z:
 assert z.testzip() is None and a.namelist()==z.namelist()
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==[m['target']]
 al=a.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 bl=z.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 assert len(al)==len(bl)==42 and al[:10]==bl[:10]
 old=[json.loads(l) for l in al];new=[json.loads(l) for l in bl];restored=deepcopy(new)
 assert new[10]['CLs'][0]==old[10]['CLs'][0]=={'__type':'LD','Var':'BoxPacking_M[15]'}
 counter=[0]
 def reverse(v,path):
  if isinstance(v,dict):
   for k,value in v.items():
    if k=='Var' and isinstance(value,str):
     match=re.fullmatch(r'BoxPacking_M\[(\d+)\]',value)
     if match and int(match[1])>=16:
      v[k]=f'BoxPacking_M[{int(match[1])-1}]';counter[0]+=1
     elif match and int(match[1])==15:assert path+[k]==[10,'CLs',0,'Var']
    else:reverse(value,path+[k])
  elif isinstance(v,list):
   for i,value in enumerate(v):reverse(value,path+[i])
 for i in range(10,len(restored)):reverse(restored[i],[i])
 assert restored==old and counter[0]==m['changed_refs']
 indices=[int(re.fullmatch(r'BoxPacking_M\[(\d+)\]',c['Var'])[1]) for r in new for c in r['CLs'] if c['__type']=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',c.get('Var',''))]
 assert indices==list(range(1,50)) and len(set(indices))==49
 # 境界工程の前段接点と自己保持・コイルを個別に照合する。
 assert new[10]['CLs'][2]['Var']=='BoxPacking_M[16]'
 assert new[10]['CLs'][5]['Var']=='BoxPacking_M[16]'

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
# 検査済みC版の保存後に、明示されたフォルダ内の旧B版のみを移動する。
os.rename(src,archive)
assert not src.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()==m['source_sha256']
m['archived']=True
m['independent_verification']={'reverse_mapping_matches_source':True,'changed_refs':counter[0],'coil_range':[1,49],'duplicates':0,'gaps':0,'first_10_rows_byte_identical':True,'boundary_predecessor_contact_preserved':True,'other_parts_identical':m['preserved_parts'],'ST_text_unchanged':True,'source_archived_byte_identical':True}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(dest),'archive':str(archive),'verification':m['independent_verification'],'output_sha256':m['output_sha256']},ensure_ascii=False))
