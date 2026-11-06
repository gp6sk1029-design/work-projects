"""保存済みA/B両版を再読込みし、全JSON要素を独立に照合する。"""
from pathlib import Path
import json,zipfile,re,hashlib,sys,collections
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
report=json.loads((b/'verification.json').read_text(encoding='utf-8'))
source=Path(report['source']); output=Path(report['output'])
target=report['changed_entries'][0]
changes=[]; variables=0
def compare(x,y,path):
 global variables
 assert type(x)==type(y),(path,'型不一致')
 if isinstance(x,dict):
  assert list(x)==list(y),(path,'キー変更')
  for k in x: compare(x[k],y[k],path+[k])
 elif isinstance(x,list):
  assert len(x)==len(y),(path,'要素数変更')
  for i in range(len(x)):compare(x[i],y[i],path+[i])
 else:
  expect=x
  if path[-1]=='Var':
   variables+=1
   m=re.fullmatch(r'Destacker_M\[(\d+)\]',x) if isinstance(x,str) else None
   if path[0]>=7 and m and int(m[1])>=7:
    expect='Destacker_M['+str(int(m[1])+4)+']'
    changes.append({'行':path[0],'変更前':x,'変更後':expect})
  assert y==expect,(path,x,y,expect)
with zipfile.ZipFile(source) as a,zipfile.ZipFile(output) as z:
 assert a.testzip() is None and z.testzip() is None
 assert a.namelist()==z.namelist()
 changed=[n for n in a.namelist() if a.read(n)!=z.read(n)]
 assert changed==[target]
 al=a.read(target).decode('utf-8-sig').splitlines()
 bl=z.read(target).decode('utf-8-sig').splitlines()
 assert len(al)==len(bl)==17 and al[:7]==bl[:7]
 compare([json.loads(l) for l in al],[json.loads(l) for l in bl],[])
 assert len(changes)==33
 assert hashlib.sha256(source.read_bytes()).hexdigest()==report['source_sha256']
 assert hashlib.sha256(output.read_bytes()).hexdigest()==report['output_sha256']
 result={'検証':'合格','対象セクション':'Destacker_段バラシ','表示行':list(range(7,17)),'参照照合数':variables,'変更数':len(changes),'変換別件数':dict(collections.Counter(c['変更前']+'→'+c['変更後'] for c in changes)),'対象外209エントリ':'全バイト一致','0～6行目':'全バイト一致','JSON要素と構造':'指定Var以外はすべて保持','原本ハッシュ':'一致','保存後ハッシュ':'一致','ZIP_CRC':'両版正常','Sysmac読込・全体再ビルド':'未実施','PLC接続・転送':'未実施'}
 (b/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
