"""保存されたB/C両版を独立照合し、段番号以外の全要素を確認する。"""
from pathlib import Path
import zipfile,json,re,hashlib,sys,collections
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
info=json.loads((b/'build_verification.json').read_text(encoding='utf-8'))
src=Path(info['source']);dst=Path(info['output']);modified=0;allvars=0
def compare(a,c,path):
 global modified,allvars
 assert type(a)==type(c)
 if isinstance(a,dict):
  assert list(a)==list(c)
  for k in a:compare(a[k],c[k],path+[k])
 elif isinstance(a,list):
  assert len(a)==len(c)
  for i in range(len(a)):compare(a[i],c[i],path+[i])
 else:
  expected=a
  if path[-1]=='Var':
   allvars+=1
   if path[0]>=10 and isinstance(a,str) and a.startswith('BoxPacking_M[') and a.endswith(']'):
    n=int(a[13:-1])
    if n>=14:expected=f'BoxPacking_M[{n+1}]';modified+=1
  assert c==expected,(path,a,c,expected)
def objects(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from objects(v)
 elif isinstance(x,list):
  for v in x:yield from objects(v)
with zipfile.ZipFile(src) as a,zipfile.ZipFile(dst) as z:
 assert a.testzip() is None and z.testzip() is None and a.namelist()==z.namelist()
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==[info['target']]
 al=a.read(info['target']).decode('utf-8-sig').splitlines();cl=z.read(info['target']).decode('utf-8-sig').splitlines()
 assert len(al)==len(cl)==28 and al[:10]==cl[:10]
 old=[json.loads(l) for l in al];new=[json.loads(l) for l in cl]
 compare(old,new,[]);assert modified==58
 vars=list(objects(new))
 coils=[e['Var'] for e in vars if e.get('__type')=='ST' and re.fullmatch(r'BoxPacking_M\[\d+\]',e.get('Var',''))]
 assert coils==[f'BoxPacking_M[{i}]' for i in range(1,33)]
 contactonly={e['Var'] for e in vars if e.get('__type')=='LD' and re.fullmatch(r'BoxPacking_M\[\d+\]',e.get('Var',''))}-set(coils)
 assert not contactonly
 assert new[9]['CLs']==old[9]['CLs']
 assert new[10]['CLs'][0]['Var']==old[10]['CLs'][0]['Var']=='BoxPacking_M[13]'
 declarations=[]
 for n in z.namelist():
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  if t.startswith('[SLWD'):
   for line in t.splitlines():
    if '\tN=BoxPacking_M\t' in line:
     m=re.search(r'ARRAY\[(\d+)\.\.(\d+)\]',line);assert m and int(m[1])<=1 and int(m[2])>=32;declarations.append(line)
 assert declarations
 assert hashlib.sha256(src.read_bytes()).hexdigest()==info['source_sha256']
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==info['output_sha256']
 report={'検証':'合格','output':str(dst),'sha256':info['output_sha256'],'参照照合数':allvars,'変更参照数':modified,'コイル番号':'1～32の連番','欠番':[],'重複':[],'コイルがない接点番号':[],'0～9行目':'全バイト一致','10行目先頭接点':'元B版どおりBoxPacking_M[13]を保持','対象外構造・変数・コメント':'一致','他構成部品数':len(z.namelist())-1,'他構成部品':'全バイト一致','配列範囲':'1～32は宣言内','B版原本':'ハッシュ一致','ZIP_CRC':'正常','SysmacStudio読込・全体再ビルド':'未実施','PLC接続と転送':'未実施'}
 (b/'independent_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
