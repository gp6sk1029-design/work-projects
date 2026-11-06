"""D版の箱詰めXピッチを専用設定変数に変更し、検証用ファイルを作る。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
from lxml import etree as E
import hashlib,json,io,re

base=Path(__file__).parent
outdir=base.parents[1]/'outputs/box-x-pitch-20261104'
outdir.mkdir(parents=True,exist_ok=True)
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104D.smc2')
stage=base/src.name
backup=outdir/(src.stem+'_ピッチ変数変更前.smc2')
raw=src.read_bytes();sha=hashlib.sha256(raw).hexdigest()
if backup.exists():assert backup.read_bytes()==raw,'バックアップと現在のD版が異なるため停止'
if stage.exists():
 oldmeta=json.loads((base/'verification.json').read_text(encoding='utf-8'))
 assert not oldmeta['published'] and hashlib.sha256(stage.read_bytes()).hexdigest()==oldmeta['output_sha256']
pitch='HMI_Box_X_Pitch_mm'
comment='箱詰めX方向の1ピッチ [mm]：符号付き。正=座標増、負=座標減。使用前に設定。'

def fields(text):
 return [dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p) for line in text.splitlines() if line.startswith('++D=')]

def enc(old,text):return (b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')

with ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 sections=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'})
 candidates=[s for s in sections if s['name']=='BoxPacking_箱詰め'];assert len(candidates)==1
 part=candidates[0]['part'];prefix=part.rsplit('/',1)[0]+'/'
 localpart=prefix+'86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml';globalpart=prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml'
 for n in z.namelist():
  t=z.read(n).decode('utf-8-sig',errors='replace')
  if t.startswith('[SLWD'):assert pitch.casefold() not in {d['N'].casefold() for d in fields(t)},'新変数名が既に存在する'
 original=z.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 rows=[json.loads(l) for l in lines];assert len(rows)==28
 row=deepcopy(rows[27]);sts=[c for c in row['CLs'] if c['__type']=='IST'];assert len(sts)==1
 cell=sts[0];oldst=cell['TXT'];assert oldst.count('HMI_RCON2_2_OUT_TargetPos[4]')==4
 cell['TXT']=oldst.replace('HMI_RCON2_2_OUT_TargetPos[4]',pitch)
 assert row['CMT'].count('Xピッチ＝設定[4]')==1
 row['CMT']=row['CMT'].replace('Xピッチ＝設定[4]',f'Xピッチ＝{pitch}').replace('設定[3][4]の数値は未設定のため使用前に入力。',f'設定[3]と{pitch}の数値は使用前に入力。')
 ending='\r\n' if lines[27].endswith('\r\n') else '\n' if lines[27].endswith('\n') else ''
 lines[27]=json.dumps(row,ensure_ascii=False,separators=(',',':'))+ending
 lr=z.read(localpart);gr=z.read(globalpart)
 lt=lr.decode('utf-8-sig');gt=gr.decode('utf-8-sig')
 assert lt.endswith('\r\n') and gt.endswith('\r\n')
 assert re.findall(r'^\+GN=([^\t\r\n]+)',lt,re.M)[-1]=='VAR_EXTERNAL'
 assert re.findall(r'^\+GN=([^\t\r\n]+)',gt,re.M)[-1]=='VAR_GLOBAL'
 # 旧[4]の今回追加したピッチ用途コメントだけを除去する。
 vline=next(l for l in lt.splitlines() if '\tN=HMI_RCON2_2_OUT_TargetPos\t' in l)
 em=re.search(r'\tEC=(<ECs>.*</ECs>)',vline);assert em
 ec=E.fromstring(em.group(1).encode());old4=[c for c in ec if c.get('EK')=='[4]'];assert len(old4)==1 and '箱内Xピッチ' in old4[0].get('C','')
 ec.remove(old4[0]);nvline=vline.replace(em.group(1),E.tostring(ec,encoding='unicode'))
 nlt=lt.replace(vline,nvline)+f'++D=LREAL\tN={pitch}\tG=VAR_EXTERNAL\tConst=0\tRO=0\tCom={comment}\r\n'
 ngt=gt+f'++D=LREAL\tN={pitch}\tR=1\tG=VAR_GLOBAL\tConst=0\tRO=0\tCom={comment}\r\n'
 assert len(fields(nlt))==len(fields(lt))+1 and len(fields(ngt))==len(fields(gt))+1
 patches={part:enc(original,''.join(lines)),localpart:enc(lr,nlt),globalpart:enc(gr,ngt)}
 stream=io.BytesIO()
 with ZipFile(stream,'w') as w:
  w.comment=z.comment
  for info in z.infolist():w.writestr(copy(info),patches.get(info.filename,z.read(info.filename)))
 data=stream.getvalue()
 with ZipFile(io.BytesIO(data)) as w:
  assert w.testzip() is None and w.namelist()==z.namelist()
  changed=[n for n in z.namelist() if z.read(n)!=w.read(n)];assert set(changed)==set(patches)
 assert src.read_bytes()==raw
 if not backup.exists():
  with backup.open('xb') as f:f.write(raw)
 with stage.open('wb') as f:f.write(data)
 stfile=outdir/'箱詰めX軸_専用ピッチ変数.st';stfile.write_bytes(b'\xef\xbb\xbf'+cell['TXT'].encode('utf-8'))
 report={'source':str(src),'output':str(src),'backup':str(backup),'staged':str(stage),'source_sha256':sha,'output_sha256':hashlib.sha256(data).hexdigest(),'target':part,'localpart':localpart,'globalpart':globalpart,'pitch':pitch,'changed_parts':changed,'preserved_parts':len(z.namelist())-3,'new_global':{'name':pitch,'type':'LREAL','retain':True},'new_external':pitch,'ST':str(stfile),'native_validation':None,'full_Sysmac_build':'未実施','published':False}
 (base/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['ST','localpart','globalpart']},ensure_ascii=False))
