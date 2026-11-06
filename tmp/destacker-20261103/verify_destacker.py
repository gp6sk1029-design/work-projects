"""保存済みA/Bを独立に再読込みし、全要素の期待値を照合する。"""
from pathlib import Path
import json,zipfile,re,hashlib,sys,collections
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
r=json.loads((b/'verification.json').read_text(encoding='utf-8'))
src=Path(r['source']);dst=Path(r['output']);target=r['changed_entries'][0]
references=0;changes=[]
def compare(a,z,path):
 global references
 assert type(a)==type(z)
 if isinstance(a,dict):
  assert list(a)==list(z)
  for k in a:compare(a[k],z[k],path+[k])
 elif isinstance(a,list):
  assert len(a)==len(z)
  for i in range(len(a)):compare(a[i],z[i],path+[i])
 else:
  expected=a
  if path[-1]=='Var':
   references+=1
   if path[0]>=9 and isinstance(a,str) and a.startswith('Destacker_M[') and a.endswith(']'):
    n=int(a[len('Destacker_M['):-1])
    if n>=11:
     expected=f'Destacker_M[{n+2}]';changes.append((path[0],a,expected))
  assert z==expected,(path,a,z,expected)
with zipfile.ZipFile(src) as a,zipfile.ZipFile(dst) as z:
 assert a.testzip() is None and z.testzip() is None
 assert a.namelist()==z.namelist()
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==[target]
 al=a.read(target).decode('utf-8-sig').splitlines();bl=z.read(target).decode('utf-8-sig').splitlines()
 assert len(al)==len(bl)==19 and al[:9]==bl[:9]
 compare([json.loads(l) for l in al],[json.loads(l) for l in bl],[])
 assert len(changes)==32
 assert hashlib.sha256(src.read_bytes()).hexdigest()==r['source_sha256']
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==r['output_sha256']
 result={'検証':'合格','対象':'Destacker_段バラシ','行範囲':[9,18],'全変数参照の照合数':references,'変更数':len(changes),'変換別件数':dict(collections.Counter(x+'→'+y for _,x,y in changes)),'0～8行目':'全バイト一致','対象外構成ファイル数':len(a.namelist())-1,'対象外構成ファイル':'全バイト一致','JSON全構造と他の値':'不変','原本ハッシュ':'一致','B版ハッシュ':'一致','ZIP_CRC':'両版正常','対象外の既存コイル重複':'4・5行目のDestacker_M[8]を保持','Sysmac読込・全体再ビルド':'未実施','PLC接続・転送':'未実施'}
 (b/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
