"""既存27行目のXYインラインSTを、X=27行目、Y=28行目へ分離する。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
from lxml import etree as E
import hashlib,json,io,uuid

b=Path(__file__).parent
out=b.parents[1]/'outputs/box-y-row28-20261104';out.mkdir(parents=True,exist_ok=True)
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104D.smc2')
stage=b/src.name;backup=out/(src.stem+'_Y軸行分離前.smc2')
assert not stage.exists() and not backup.exists()
raw=src.read_bytes();sha=hashlib.sha256(raw).hexdigest()
with ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None
 sections=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   for e in E.fromstring(z.read(n)).iter():
    if e.get('type')=='PouBody':sections.append({'name':e.get('name'),'part':n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'})
 targets=[s for s in sections if s['name']=='BoxPacking_箱詰め'];assert len(targets)==1
 part=targets[0]['part'];orig=z.read(part);lines=orig.decode('utf-8-sig').splitlines(keepends=True)
 rows=[json.loads(l) for l in lines];assert len(rows)==28
 row=deepcopy(rows[27]);cells=[c for c in row['CLs'] if c['__type']=='IST'];assert len(cells)==1
 cell=cells[0];marker='// 箱詰めY位置：';assert cell['TXT'].count(marker)==1
 xst,yst=cell['TXT'].split(marker,1);xst=xst.removesuffix('\r\n');yst=marker+yst
 assert xst.endswith('END_IF;\r\n') and yst.endswith('END_IF;\r\n')
 assert 'RCON2_3_OUT_TargetPos_mm' not in xst and 'RCON2_2_OUT_TargetPos_mm' not in yst
 assert 'HMI_Box_X_Pitch_mm' in xst and 'HMI_Box_Y_Pitch_mm' in yst
 assert cell['TXT']==xst+'\r\n'+yst
 cell['TXT']=xst
 row['CMT']='RCON2_4：取出し上昇完了 → 箱詰めX目標位置の設定\r\nX開始位置＝HMI_RCON2_2_OUT_TargetPos[3]、Xピッチ＝HMI_Box_X_Pitch_mm。\r\n既存M[32]コイルと同じ条件でX位置を転送。Yは次の28行目で転送。\r\n4列×4行、5個積み×16か所＝80個。開始位置・ピッチは使用前に設定。'
 eid=str(uuid.uuid4());assert all(eid.encode() not in z.read(n) for n in z.namelist())
 newrow={'CLs':[{'__type':'LD','Var':'BoxPacking_M[32]'}, {'__type':'IST','EID':eid,'H':1000,'Ix':1,'TXT':yst,'W':825,'X':1}], 'CMT':'箱詰めY目標位置の設定（27行目の成立状態M[32]で実行）\r\nY開始位置＝HMI_RCON2_3_OUT_TargetPos[3]、Yピッチ＝HMI_Box_Y_Pitch_mm。\r\nカウント5～20：基準、25～40：＋1ピッチ、45～60：＋2、65～80：＋3。\r\n5個単位の有効カウントだけ転送。移動開始・加算・リセットは行わない。', 'LRI':2,'RRI':3,'VLs':[]}
 def line(r):return json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n'
 lines[27]=line(row);lines.append(line(newrow))
 patched=(b'\xef\xbb\xbf' if orig.startswith(b'\xef\xbb\xbf') else b'')+''.join(lines).encode('utf-8')
 buf=io.BytesIO()
 with ZipFile(buf,'w') as w:
  w.comment=z.comment
  for info in z.infolist():w.writestr(copy(info),patched if info.filename==part else z.read(info.filename))
 data=buf.getvalue()
 with ZipFile(io.BytesIO(data)) as w:
  assert w.testzip() is None and w.namelist()==z.namelist()
  changes=[n for n in z.namelist() if z.read(n)!=w.read(n)];assert changes==[part]
 assert src.read_bytes()==raw
 with backup.open('xb') as f:f.write(raw)
 with stage.open('xb') as f:f.write(data)
 (out/'27行目_X軸.st').write_bytes(b'\xef\xbb\xbf'+xst.encode('utf-8'))
 (out/'28行目_Y軸.st').write_bytes(b'\xef\xbb\xbf'+yst.encode('utf-8'))
 report={'source':str(src),'output':str(src),'backup':str(backup),'staged':str(stage),'source_sha256':sha,'output_sha256':hashlib.sha256(data).hexdigest(),'target':part,'changed_parts':changes,'preserved_parts':len(z.namelist())-1,'new_row':28,'old_row_count':28,'new_row_count':29,'new_IST_ID':eid,'native_validation':None,'published':False,'full_Sysmac_build':'未実施'}
 (b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
