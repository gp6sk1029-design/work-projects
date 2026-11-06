"""箱詰め27行目に既存条件と並列のX軸インラインSTだけを追加する。"""
from pathlib import Path
from copy import copy,deepcopy
from zipfile import ZipFile
from lxml import etree as E
import hashlib,json,re,io,uuid

base=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104C.smc2')
dst=src.with_name(src.name.replace('20261104C.smc2','20261104D.smc2'))
stage=base/dst.name
raw=src.read_bytes();sha=hashlib.sha256(raw).hexdigest()
assert sha=='d42d09dde68fa4d0a7159662610c7820982e267f3723ed1a7d1260aae95c9097'
assert not dst.exists() and not stage.exists(),'既存出力を上書きしない'
st='''// 箱詰めX位置：4列×4行、1か所5個積み、合計80個
// Box_Total_CTは既存ラダーで5個ずつ加算済みの値を使用する。
// X開始位置：HMI_RCON2_2_OUT_TargetPos[3] [mm]
// Xピッチ　：HMI_RCON2_2_OUT_TargetPos[4] [mm]（符号付き）
// 無効カウントでは目標を更新しない。加算・リセット・移動開始は行わない。

// 1列目：開始位置
IF (Box_Total_CT = INT#5) OR
   (Box_Total_CT = INT#25) OR
   (Box_Total_CT = INT#45) OR
   (Box_Total_CT = INT#65) THEN

    RCON2_2_OUT_TargetPos_mm := HMI_RCON2_2_OUT_TargetPos[3];

// 2列目：開始位置＋1ピッチ
ELSIF (Box_Total_CT = INT#10) OR
      (Box_Total_CT = INT#30) OR
      (Box_Total_CT = INT#50) OR
      (Box_Total_CT = INT#70) THEN

    RCON2_2_OUT_TargetPos_mm :=
        HMI_RCON2_2_OUT_TargetPos[3] +
        HMI_RCON2_2_OUT_TargetPos[4];

// 3列目：開始位置＋2ピッチ
ELSIF (Box_Total_CT = INT#15) OR
      (Box_Total_CT = INT#35) OR
      (Box_Total_CT = INT#55) OR
      (Box_Total_CT = INT#75) THEN

    RCON2_2_OUT_TargetPos_mm :=
        HMI_RCON2_2_OUT_TargetPos[3] +
        HMI_RCON2_2_OUT_TargetPos[4] * LREAL#2.0;

// 4列目：開始位置＋3ピッチ
ELSIF (Box_Total_CT = INT#20) OR
      (Box_Total_CT = INT#40) OR
      (Box_Total_CT = INT#60) OR
      (Box_Total_CT = INT#80) THEN

    RCON2_2_OUT_TargetPos_mm :=
        HMI_RCON2_2_OUT_TargetPos[3] +
        HMI_RCON2_2_OUT_TargetPos[4] * LREAL#3.0;
END_IF;
'''.replace('\n','\r\n')

with ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 sections=[]
 for name in z.namelist():
  if name.endswith('.oem'):
   for e in E.fromstring(z.read(name)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':name.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'})
 targets=[s for s in sections if s['name']=='BoxPacking_箱詰め'];assert len(targets)==1
 part=targets[0]['part'];prefix=part.rsplit('/',1)[0]+'/'
 localpart=prefix+'86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml'
 globalpart=prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml'
 localraw=z.read(localpart);local=localraw.decode('utf-8-sig');globaltext=z.read(globalpart).decode('utf-8-sig')
 assert '++D=INT\tN=Box_Total_CT\tG=VAR_EXTERNAL\t' in local
 assert '++D=INT\tN=Box_Total_CT\tG=VAR_GLOBAL\t' in globaltext
 assert 'N=RCON2_2_OUT_TargetPos_mm\t' in local
 for name in z.namelist():
  text=z.read(name).decode('utf-8-sig',errors='replace')
  if not text.lstrip().startswith('{'):continue
  assert not re.search(r'HMI_RCON2_2_OUT_TargetPos\[(?:3|4)\]',text),'設定[3][4]に既存使用あり'
 original=z.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 rows=[json.loads(line) for line in lines];assert len(rows)==28
 old=rows[27];assert [e.get('Var') for e in old['CLs'] if e['__type']=='ST']==['BoxPacking_M[32]']
 assert old['CLs'][0]['Var']=='BoxPacking_M[31]' and old['CLs'][1]['Var']=='RCON2_4_MoveDone'
 assert old['VLs']==[{'Ix':7,'X':2}]
 assert all('Box_Total_CT' in json.dumps(rows[i]) and 'INT#5' in json.dumps(rows[i]) for i in [13,14])
 row=deepcopy(old)
 eid=str(uuid.uuid4());assert all(eid.encode() not in z.read(n) for n in z.namelist())
 row['CLs'].append({'__type':'IST','EID':eid,'H':1075,'Ix':8,'TXT':st,'W':825,'X':3,'Y':1})
 row['VLs'].append({'Ix':9,'X':3})
 row['CMT']='RCON2_4：取出し上昇完了 → 箱詰めX目標位置の設定\r\n4列×4行、5個積み×16か所＝80個。Box_Total_CTは5個単位。\r\n箱詰めX開始位置＝設定[3]、Xピッチ＝設定[4]（mm・符号付き）。\r\n既存M[32]コイルと同じ条件でX位置だけ転送。Y/Z・移動開始・カウント処理は追加しない。\r\n設定[3][4]の数値は未設定のため使用前に入力。'
 ending='\r\n' if lines[27].endswith('\r\n') else '\n' if lines[27].endswith('\n') else ''
 lines[27]=json.dumps(row,ensure_ascii=False,separators=(',',':'))+ending
 def encode(old,text):return (b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
 targetline=next(line for line in local.splitlines() if '\tN=HMI_RCON2_2_OUT_TargetPos\t' in line)
 ec_match=re.search(r'\tEC=(<ECs>.*</ECs>)',targetline);assert ec_match
 ec=E.fromstring(ec_match.group(1).encode());assert {e.get('EK') for e in ec}=={'[1]','[2]'}
 E.SubElement(ec,'EC',EK='[3]',C='箱内X開始位置 [mm]：5個積みの1列目（設定値を入力）')
 E.SubElement(ec,'EC',EK='[4]',C='箱内Xピッチ [mm]：符号付き、2列目以降へ加算（設定値を入力）')
 changedline=targetline.replace(ec_match.group(1),E.tostring(ec,encoding='unicode'))
 newlocal=local.replace(targetline,changedline);assert local.count(targetline)==1
 patches={part:encode(original,''.join(lines)),localpart:encode(localraw,newlocal)}
 out=io.BytesIO()
 with ZipFile(out,'w') as w:
  w.comment=z.comment
  for info in z.infolist():w.writestr(copy(info),patches.get(info.filename,z.read(info.filename)))
 data=out.getvalue()
 with ZipFile(io.BytesIO(data)) as w:
  assert w.testzip() is None and w.namelist()==z.namelist()
  changed=[n for n in z.namelist() if z.read(n)!=w.read(n)];assert set(changed)==set(patches)
  final=[json.loads(l) for l in w.read(part).decode('utf-8-sig').splitlines()]
  assert final[:27]==rows[:27] and len(final)==len(rows) and final[27]==row
  restored=deepcopy(row);restored['CLs'].pop();restored['VLs'].pop();del restored['CMT'];assert restored==old
  ladder_counts={s['part']:len(w.read(s['part']).decode('utf-8-sig').splitlines()) for s in sections if w.read(s['part']).lstrip(b'\xef\xbb\xbf').startswith(b'{"CLs"')}
 assert src.read_bytes()==raw
 with stage.open('xb') as f:f.write(data)
 stfile=base/'箱詰めX軸_27行目.st';stfile.write_bytes(b'\xef\xbb\xbf'+st.encode('utf-8'))
 report={'source':str(src),'output':str(dst),'staged':str(stage),'source_sha256':sha,'output_sha256':hashlib.sha256(data).hexdigest(),'target':part,'row':27,'row_count':28,'changed_parts':changed,'preserved_parts':len(z.namelist())-2,'ladder_counts':ladder_counts,'new_declarations':0,'new_IST_ID':eid,'ST':str(stfile),'native_validation':None,'full_Sysmac_build':'未実施','PLC_transfer':'未実施'}
 (base/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['ladder_counts']},ensure_ascii=False))
