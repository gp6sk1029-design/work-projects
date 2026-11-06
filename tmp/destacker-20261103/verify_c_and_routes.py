"""保存済みC版を独立照合し、指令コイルと受け側接点の対応表を作る。"""
from pathlib import Path
from lxml import etree as E
import json,zipfile,re,hashlib,collections,sys,csv
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).parent
info=json.loads((base/'C版修正検証.json').read_text(encoding='utf-8'))
src=Path(info['source']);dst=Path(info['output']);target=info['target'];changes=0
def verify(a,c,path):
 global changes
 assert type(a)==type(c)
 if isinstance(a,dict):
  assert list(a)==list(c)
  for k in a:verify(a[k],c[k],path+[k])
 elif isinstance(a,list):
  assert len(a)==len(c)
  for i in range(len(a)):verify(a[i],c[i],path+[i])
 else:
  expected=a
  if path[-1]=='Var' and isinstance(a,str):
   m=re.fullmatch(r'Destacker_M\[(\d+)\]',a)
   if m:
    n=int(m[1]);mapping={**{i:i for i in range(1,6)},7:6,9:8,**{i:i-1 for i in range(10,26)}}
    if n==8:
     # ラダー位置を使う編集処理とは別に、元JSONの要素パスで照合する。
     fixed={(4,'CLs',2,'Var'):7,(4,'CLs',6,'Var'):7,(5,'CLs',0,'Var'):7,(5,'CLs',2,'Var'):8,(5,'CLs',6,'Var'):8}
     replacement=fixed[tuple(path)]
    else:replacement=mapping[n]
    expected=f'Destacker_M[{replacement}]'
  assert c==expected,(path,a,c,expected)
  if a!=c:changes+=1
def elements(x,path):
 if isinstance(x,dict):
  if 'Var' in x:yield {'path':path,**x}
  for k,v in x.items():yield from elements(v,path+[k])
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from elements(v,path+[i])
with zipfile.ZipFile(src) as old,zipfile.ZipFile(dst) as z:
 assert old.testzip() is None and z.testzip() is None
 assert old.namelist()==z.namelist()
 assert [n for n in old.namelist() if old.read(n)!=z.read(n)]==[target]
 before=[json.loads(l) for l in old.read(target).decode('utf-8-sig').splitlines()]
 rows=[json.loads(l) for l in z.read(target).decode('utf-8-sig').splitlines()]
 verify(before,rows,[]);assert changes==53
 es=list(elements(rows,[]))
 coils=[int(re.fullmatch(r'Destacker_M\[(\d+)\]',e['Var'])[1]) for e in es if e.get('__type')=='ST' and re.fullmatch(r'Destacker_M\[\d+\]',e['Var'])]
 assert coils==list(range(1,25))
 refs=[int(re.fullmatch(r'Destacker_M\[(\d+)\]',e['Var'])[1]) for e in es if re.fullmatch(r'Destacker_M\[\d+\]',e['Var'])]
 assert set(refs)==set(coils)
 sections={}
 for name in z.namelist():
  if not name.endswith('.oem'):continue
  root=E.fromstring(z.read(name));folder=name.rsplit('/',1)[0]
  for e in root.iter():
   if e.get('name') in ['Output_出力','RCON_IAI'] and e.get('type')=='PouBody':sections[e.get('name')]=folder+'/'+e.get('id')+'.xml'
 assert set(sections)=={'Output_出力','RCON_IAI'}
 receiving={name:[json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines() if l.strip()] for name,part in sections.items()}
 outgoing=[e for e in es if e.get('__type')=='ST' and (e['Var'].startswith('Out_') or e['Var'].startswith('RCON'))]
 names=sorted({e['Var'] for e in outgoing});routes=[]
 for name in names:
  section='Output_出力' if name.startswith('Out_') else 'RCON_IAI'
  allitems=list(elements(receiving[section],[]))
  matches=[e for e in allitems if e.get('__type')=='LD' and e['Var']==name]
  command_rows=[];monitor_rows=[]
  expected=name.split('_Auto[')[0] if section=='Output_出力' else 'RCON2_1_M[1]'
  for match in matches:
   i=match['path'][0]
   coilvars=[e['Var'] for e in elements(receiving[section][i],[]) if e.get('__type')=='ST']
   (command_rows if expected in coilvars else monitor_rows).append(i)
  routes.append({'変数':name,'送信元行':sorted(e['path'][0] for e in outgoing if e['Var']==name),'受信先':section,'駆動接点行':sorted(set(command_rows)),'監視等接点行':sorted(set(monitor_rows)),'駆動コイル':expected,'接点数':len(matches),'合致':bool(command_rows),'正接点':all(not e.get('Not',False) for e in matches)})
 assert len(routes)==12 and all(r['合致'] and r['正接点'] for r in routes)
 duplicates={r['変数']:r['送信元行'] for r in routes if len(r['送信元行'])>1}
 assert len(duplicates)==4
 assert hashlib.sha256(src.read_bytes()).hexdigest()==info['source_sha256']
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==info['output_sha256']
 result={'C版':str(dst),'SHA256':info['output_sha256'],'段番号変更数':changes,'コイル順':coils,'段番号欠番':[],'段番号重複':[],'接点だけの段番号':[],'他209部品':'全バイト一致','JSON構造と他変数':'不変','B版原本':'ハッシュ一致','出力向け種類数':sum(r['受信先']=='Output_出力' for r in routes),'RCON向け種類数':sum(r['受信先']=='RCON_IAI' for r in routes),'指令コイル箇所数':len(outgoing),'駆動先接点未登録':[],'指令コイル重複使用':duplicates,'対応表':routes,'Sysmac読込みと全体再ビルド':'未実施','実機動作確認':'未実施'}
 (base/'C版独立照合と接点確認.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 with (base/'接点割付確認一覧.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(routes[0]));w.writeheader();w.writerows(routes)
 print(json.dumps({k:v for k,v in result.items() if k!='対応表'},ensure_ascii=False))
