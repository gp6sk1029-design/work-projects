"""現在のD版の27行目へY座標計算と専用ピッチ変数を追加する。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
from lxml import etree as E
import hashlib,json,re,io

base=Path(__file__).parent
outdir=base.parents[1]/'outputs/box-y-pitch-20261104';outdir.mkdir(parents=True,exist_ok=True)
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104D.smc2')
stage=base/src.name;backup=outdir/(src.stem+'_Y軸追加前.smc2')
assert not stage.exists() and not backup.exists(),'既存の検証用ファイルを上書きしない'
raw=src.read_bytes();sha=hashlib.sha256(raw).hexdigest()
pitch='HMI_Box_Y_Pitch_mm'
comment='箱詰めY方向の1ピッチ [mm]：符号付き。正=座標増、負=座標減。使用前に設定。'
yst='''// 箱詰めY位置：X方向4か所（20個）ごとに次の行へ進む。
// Y開始位置：HMI_RCON2_3_OUT_TargetPos[3] [mm]
// Yピッチ　：HMI_Box_Y_Pitch_mm [mm]（符号付き）
// 位置選択前に既存ラダーで5個加算。無効カウントでは目標を更新しない。

// 1行目：開始位置
IF (Box_Total_CT = INT#5) OR
   (Box_Total_CT = INT#10) OR
   (Box_Total_CT = INT#15) OR
   (Box_Total_CT = INT#20) THEN

    RCON2_3_OUT_TargetPos_mm := HMI_RCON2_3_OUT_TargetPos[3];

// 2行目：開始位置＋1ピッチ
ELSIF (Box_Total_CT = INT#25) OR
      (Box_Total_CT = INT#30) OR
      (Box_Total_CT = INT#35) OR
      (Box_Total_CT = INT#40) THEN

    RCON2_3_OUT_TargetPos_mm :=
        HMI_RCON2_3_OUT_TargetPos[3] + HMI_Box_Y_Pitch_mm;

// 3行目：開始位置＋2ピッチ
ELSIF (Box_Total_CT = INT#45) OR
      (Box_Total_CT = INT#50) OR
      (Box_Total_CT = INT#55) OR
      (Box_Total_CT = INT#60) THEN

    RCON2_3_OUT_TargetPos_mm :=
        HMI_RCON2_3_OUT_TargetPos[3] + HMI_Box_Y_Pitch_mm * LREAL#2.0;

// 4行目：開始位置＋3ピッチ
ELSIF (Box_Total_CT = INT#65) OR
      (Box_Total_CT = INT#70) OR
      (Box_Total_CT = INT#75) OR
      (Box_Total_CT = INT#80) THEN

    RCON2_3_OUT_TargetPos_mm :=
        HMI_RCON2_3_OUT_TargetPos[3] + HMI_Box_Y_Pitch_mm * LREAL#3.0;
END_IF;
'''.replace('\n','\r\n')

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
 targets=[s for s in sections if s['name']=='BoxPacking_箱詰め'];assert len(targets)==1
 part=targets[0]['part'];prefix=part.rsplit('/',1)[0]+'/'
 localpart=prefix+'86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml';globalpart=prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml'
 for n in z.namelist():
  t=z.read(n).decode('utf-8-sig',errors='replace')
  if t.startswith('[SLWD'):assert pitch.casefold() not in {d['N'].casefold() for d in fields(t)}
  elif t.lstrip().startswith('{'):assert 'HMI_RCON2_3_OUT_TargetPos[3]' not in t,'Y開始位置設定[3]は既存使用あり'
 original=z.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 rows=[json.loads(l) for l in lines];assert len(rows)==28
 row=deepcopy(rows[27]);cells=[c for c in row['CLs'] if c['__type']=='IST'];assert len(cells)==1
 cell=cells[0];assert 'HMI_Box_X_Pitch_mm' in cell['TXT'] and 'RCON2_3_OUT_TargetPos_mm' not in cell['TXT']
 cell['TXT']+='\r\n'+yst
 row['CMT']='RCON2_4：取出し上昇完了 → 箱詰めXY目標位置の設定\r\n4列×4行、5個積み×16か所＝80個。Box_Total_CTは5個単位。\r\nX開始位置＝HMI_RCON2_2_OUT_TargetPos[3]、Xピッチ＝HMI_Box_X_Pitch_mm。\r\nY開始位置＝HMI_RCON2_3_OUT_TargetPos[3]、Yピッチ＝HMI_Box_Y_Pitch_mm。\r\n既存M[32]コイルと同じ条件でXY位置を転送。Z・移動開始・カウント処理は追加しない。\r\n開始位置とピッチはmm、符号付き。実際の値は使用前に入力。'
 ending='\r\n' if lines[27].endswith('\r\n') else '\n' if lines[27].endswith('\n') else ''
 lines[27]=json.dumps(row,ensure_ascii=False,separators=(',',':'))+ending
 lr=z.read(localpart);gr=z.read(globalpart);lt=lr.decode('utf-8-sig');gt=gr.decode('utf-8-sig')
 localdefs={d['N']:d for d in fields(lt)}
 assert localdefs['HMI_RCON2_3_OUT_TargetPos']['D']=='ARRAY[0..99] OF LREAL'
 assert localdefs['RCON2_3_OUT_TargetPos_mm']['D']=='LREAL'
 assert lt.endswith('\r\n') and gt.endswith('\r\n')
 assert re.findall(r'^\+GN=([^\t\r\n]+)',lt,re.M)[-1]=='VAR_EXTERNAL'
 assert re.findall(r'^\+GN=([^\t\r\n]+)',gt,re.M)[-1]=='VAR_GLOBAL'
 vline=next(l for l in lt.splitlines() if '\tN=HMI_RCON2_3_OUT_TargetPos\t' in l)
 em=re.search(r'\tEC=(<ECs>.*</ECs>)',vline);assert em
 ec=E.fromstring(em.group(1).encode());assert not any(c.get('EK')=='[3]' for c in ec)
 E.SubElement(ec,'EC',EK='[3]',C='箱内Y開始位置 [mm]：4列×4行の1行目（設定値を入力）')
 nvline=vline.replace(em.group(1),E.tostring(ec,encoding='unicode'))
 nlt=lt.replace(vline,nvline)+f'++D=LREAL\tN={pitch}\tG=VAR_EXTERNAL\tConst=0\tRO=0\tCom={comment}\r\n'
 ngt=gt+f'++D=LREAL\tN={pitch}\tR=1\tG=VAR_GLOBAL\tConst=0\tRO=0\tCom={comment}\r\n'
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
 with backup.open('xb') as f:f.write(raw)
 with stage.open('xb') as f:f.write(data)
 stfile=outdir/'箱詰めXY軸_27行目.st';stfile.write_bytes(b'\xef\xbb\xbf'+cell['TXT'].encode('utf-8'))
 report={'source':str(src),'output':str(src),'backup':str(backup),'staged':str(stage),'source_sha256':sha,'output_sha256':hashlib.sha256(data).hexdigest(),'target':part,'localpart':localpart,'globalpart':globalpart,'pitch':pitch,'ST':str(stfile),'changed_parts':changed,'preserved_parts':len(z.namelist())-3,'native_validation':None,'published':False,'full_Sysmac_build':'未実施'}
 (base/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['ST','localpart','globalpart']},ensure_ascii=False))
