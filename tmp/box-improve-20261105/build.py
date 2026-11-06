"""箱詰め/RCON2の確定不整合を修正。許可フラグ・実速度・位置値は変更しない。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
from lxml import etree as E
import json,re,hashlib,io,uuid
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
src=Path(d['source']);raw=src.read_bytes();assert hashlib.sha256(raw).hexdigest()==d['sha256']
dest=src.with_name(src.name.replace('20261105D.smc2','20261105E.smc2'));archive=src.parent/'履歴'/src.name;stage=b/dest.name
assert not dest.exists() and not archive.exists()
if stage.exists():
 prior=json.loads((b/'verification.json').read_text(encoding='utf-8'))
 assert not prior['published'] and hashlib.sha256(stage.read_bytes()).hexdigest()==prior['output_sha256']
assert archive.parent.resolve().is_relative_to(src.parent.resolve())
sections={s['name']:s for s in d['sections']};box=deepcopy(sections['BoxPacking_箱詰め']['rows']);rcon=deepcopy(sections['RCON_IAI']['rows']);output_name=next(n for n in sections if n.startswith('Output_'));output=deepcopy(sections[output_name]['rows'])
def ist(text,comment):return {'CLs':[{'__type':'IST','EID':str(uuid.uuid4()),'H':550,'W':900,'TXT':text.replace('\n','\r\n')}],'CMT':comment,'LRI':1,'RRI':2,'VLs':[]}
def ld(var,x=0,y=0,negative=False,ix=0):
 c={'__type':'LD','Var':var}
 if x:c['X']=x
 if y:c['Y']=y
 if negative:c['Not']=True
 if ix:c['Ix']=ix
 return c
def reindex(r):
 n=0
 for c in r['CLs']:
  if c['__type']!='HL':c['Ix']=n;n+=1
  for p in c.get('In',[])+c.get('Out',[]):
   if p['__type']=='PRM':p['Ix']=n;n+=1
 r['LRI']=n;r['RRI']=n+1;n+=2
 for v in r['VLs']:v['Ix']=n;n+=1
 return r
def request_row(axis,count):
 cells=[]
 for i in range(count):
  cells += [ld(f'RCON2_{axis}_Auto[{i+1}]',0,i),{'__type':'F','Name':'Up','In':[{'__type':'PF','Arg':'In'}],'Out':[{'__type':'PF','Arg':''}],'Id':str(uuid.uuid4()),'X':1,'Y':i}]
 cells += [ld(f'RCON2_{axis}_M[4]',2),{'__type':'ST','Var':f'RCON2_{axis}_M[5]','X':3}]
 row={'CLs':cells,'VLs':[{'X':2,'Y':i} for i in range(count-1)],'CMT':'自動要求ごとの立上りを受ける。完了100ms保持中の新要求も次行で保留し、要求番号切替をOR全体の立上りに依存させない。'}
 return reindex(row)

# コンテナ軸の同名通常コイルを別々の要求へ割り当てる。
for row,old,new in [(5,1,4),(11,2,5),(37,2,6)]:
 c=[c for c in box[row]['CLs'] if c['__type']=='ST' and c.get('Var')==f'RCON2_5_Auto[{old}]'];assert len(c)==1
 c[0]['Var']=f'RCON2_5_Auto[{new}]'
for row,old,new in [(39,'Out_CYw_Ejc_Cont_H_Auto[1]','Out_CYw_Ejc_Cont_H_Auto[3]'),(38,'Out_CYw_Ejc_Cont_F_Auto[1]','Out_CYw_Ejc_Cont_F_Auto[2]')]:
 cells=[c for c in box[row]['CLs'] if c['__type']=='ST' and c.get('Var')==old];assert len(cells)==1;cells[0]['Var']=new
# 同じ系統の全要求を、Outputの動作回路・異常監視の両方へ追加する。
output_changed=[]
for name,count in [('Out_CYw_Ejc_Cont_H_Auto',3),('Out_CYw_Ejc_Cont_F_Auto',2),('Out_CYw_Box_Chuck_H_Auto',2)]:
 for i,row in enumerate(output):
  auto=[c for c in row['CLs'] if c['__type']=='LD' and c.get('Var')==name+'[1]']
  if not auto:continue
  assert len(auto)==1 and auto[0].get('X',0)==auto[0].get('Y',0)==0
  missing=[n for n in range(2,count+1) if not any(c['__type']=='LD' and c.get('Var')==f'{name}[{n}]' for c in row['CLs'])]
  if not missing:continue
  amount=len(missing)
  for c in row['CLs']:
   if c.get('Y',0)>=1:c['Y']+=amount
  vls=[]
  for v in row['VLs']:
   if v.get('Y',0)==0:
    for y in range(amount+1):nv=deepcopy(v);nv['Y']=y;vls.append(nv)
   else:nv=deepcopy(v);nv['Y']+=amount;vls.append(nv)
  row['VLs']=vls+[{'X':1,'Y':y} for y in range(amount)]
  row['CLs'] += [ld(f'{name}[{n}]',0,y+1) for y,n in enumerate(missing)]
  row['CMT']=row.get('CMT','')+f'\r\n箱詰め自動要求[1]～[{count}]を並列に受ける。';reindex(row);output_changed.append(i)
assert box[11]['CLs'][0]['Var']=='BoxPacking_M[14]';box[11]['CLs'][0]['Var']='BoxPacking_M[16]'
assert box[36]['CLs'][1]['Var']=='RCON2_4_MoveDone' and box[36]['CLs'][1]['Not']
box[36]['CLs'][1].pop('Not');box[36]['CMT']+='\r\nZ上昇の完了ONを確認してから入数判定。'

# 有効カウントでのみ箱内移動工程と要求を開始する。
for i in [28,29]:
 r=box[i]
 for c in r['CLs']:
  if c.get('X',0)>=3:c['X']+=1
 for v in r['VLs']:
  if v.get('X',0)>=3:v['X']+=1
 r['CLs'].append(ld('Box_PackCount_Valid',3));reindex(r)
valid=ist('''// 加算済みの箱内個数を、箱内移動を選ぶ直前に確認する。
Box_PackCount_Valid := (Box_Total_CT >= INT#5) AND
                       (Box_Total_CT <= INT#80) AND
                       ((Box_Total_CT MOD INT#5) = INT#0);
''','箱内XY移動の個数確認。無効値では移動工程と自動要求を成立させない。')

# 箱交換の完了立上りでカウントをゼロへ戻す。
r=box[41];r['CLs'] += [{'__type':'HL','X':4},{'__type':'F','Name':'Up','Id':str(uuid.uuid4()),'In':[{'__type':'PF','Arg':'In'}],'Out':[{'__type':'PF','Arg':''}],'X':3,'Y':1},{'__type':'F','Name':'MOVE','In':[{'__type':'PF','Arg':'EN'},{'__type':'PRM','Arg':'In','Type':'ANY','Var':'INT#0'}],'Out':[{'__type':'PF','Arg':'ENO'},{'__type':'PRM','Arg':'Out','Type':'ANY','Var':'Box_Total_CT'}],'X':4,'Y':1,'PL':True}]
r['VLs'].append({'X':3});r['CMT']+='\r\n完了立上り時に次箱用Box_Total_CTを0へ初期化。';reindex(r)
box.insert(28,valid)

# RCON2のX/Y/Z/コンテナ軸。機械運転許可は既存変数を参照するだけ。
queue_rows={}
for axis,count in [(2,3),(3,3),(4,5),(5,6)]:
 base=283+(axis-2)*40
 # 位置・幅・速度・加減速は既存の設定変数から転送する。押付け等は従来どおり未使用。
 for off in [0,1,2,3]:
  assert rcon[base+off]['CLs'][0]['Var']=='P_Off'
  rcon[base+off]['CLs'][0]['Var']='P_On'
  rcon[base+off]['CMT']=rcon[base+off].get('CMT','').replace('（未接続）','')+'\r\n数値設定の転送のみ。移動開始は別の運転許可で制限。'
 for off in [20,21,22,23,24]:
  assert rcon[base+off]['CLs'][0]['Var']=='P_Off'
  rcon[base+off]['CLs'][0]['Var']=f'RCON2_IN[{axis}].DataValid'
  rcon[base+off]['CMT']=rcon[base+off].get('CMT','')+'\r\n入力データ有効時に監視値を更新。'
 text=f'''// 軸{axis}の運転許可。値自体をTRUEへ書き換える処理は追加しない。
RCON2_{axis}_M[4] := AutoMode AND NOT Pause[1] AND NOT M9999 AND NOT In_Sw_RESET
    AND RCON2_{axis}_Ready AND RCON2_CommOK
    AND RCON2_WriteEnable AND RCON2_LayoutConfirmed AND RCON2_ByteOrderConfirmed
    AND RCON2_AxisApply[{axis}] AND RCON2_MotionPermit[{axis}] AND RCON2_IN[{axis}].DataValid
    AND (RCON2_{axis}_OUT_Speed_mm_s > LREAL#0.0)
    AND (RCON2_{axis}_OUT_AccDec_G > LREAL#0.0)
    AND (RCON2_{axis}_OUT_PositionBand_mm >= LREAL#0.0);
// Startを出した実時間を確認し、PENDのOFFを今回指令の受付として保持する。
RCON2_{axis}_TON[3](In := RCON2_OUT[{axis}].Control.Start AND RCON2_{axis}_M[1], PT := T#20ms);
IF NOT RCON2_{axis}_M[1] OR NOT RCON2_{axis}_M[4] THEN
    RCON2_{axis}_M[2] := FALSE;
ELSIF RCON2_{axis}_TON[3].Q AND NOT RCON2_{axis}_IN_PositionDone THEN
    RCON2_{axis}_M[2] := TRUE;
END_IF;
// 受付後はStartをOFFにし、次のPEND ONを完了として待つ。
RCON2_OUT[{axis}].Control.Start := RCON2_{axis}_M[1] AND NOT RCON2_{axis}_M[2] AND RCON2_{axis}_M[4];
'''
 rcon[base+5]=ist(text,f'RCON2_{axis} 開始/受付管理：Startを20ms以上保持し、PEND OFF受付後に解除。許可喪失時は開始要求を解除（安全停止処理の代替ではない）。')
 rcon[base+38]=request_row(axis,count)
 queue_rows[base+38]=ist(f'''// 立上り要求を保留し、前指令の完了保持が終わってから次を受け付ける。
IF NOT RCON2_{axis}_M[4] THEN
    RCON2_{axis}_M[1] := FALSE;
    RCON2_{axis}_M[3] := FALSE;
ELSE
    RCON2_{axis}_M[3] := RCON2_{axis}_M[3] OR RCON2_{axis}_M[5];
    IF RCON2_{axis}_MoveDone THEN
        RCON2_{axis}_M[1] := FALSE;
    ELSIF NOT RCON2_{axis}_M[1] AND RCON2_{axis}_M[3] THEN
        RCON2_{axis}_M[1] := TRUE;
        RCON2_{axis}_M[3] := FALSE;
    END_IF;
END_IF;
''',f'RCON2_{axis} 受付保留/開始保持。完了中に次要求の立上りを失わない。許可喪失で保留を破棄。')
 # 完了は今回指令の受付済みM[2]を通過してからPEND ONの立上りで生成。
 done=rcon[base+39]
 for c in done['CLs']:
  if c.get('X',0)>=1:c['X']+=1
 for v in done['VLs']:
  if v.get('X',0)>=1:v['X']+=1
 done['CLs'] += [ld(f'RCON2_{axis}_M[2]',1),{'__type':'HL','X':1,'Y':1}]
 done['CMT']='今回指令のPEND OFF受付済みを確認し、PEND ONで動作完了。100ms保持。';reindex(done)

rcon=[element for i,row in enumerate(rcon) for element in ([row,queue_rows[i]] if i in queue_rows else [row])]

with ZipFile(io.BytesIO(raw)) as z:
 prefix=sections['RCON_IAI']['part'].rsplit('/',1)[0]+'/'
 localbox=prefix+'86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml';localrcon=prefix+'a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml';globalpart=prefix+'f07dd06c-505c-431b-b9fc-098949805b4e.xml'
 patches={}
 def encode(old,text):return (b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
 def fields(t):return {dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)['N']:dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in t.splitlines() if l.startswith('++D=')}
 rt=z.read(localrcon).decode('utf-8-sig');bt=z.read(localbox).decode('utf-8-sig');gt=z.read(globalpart).decode('utf-8-sig');rd=fields(rt);gd=fields(gt)
 assert 'Box_PackCount_Valid' not in fields(bt)
 bt=bt.replace('+GN=VAR_EXTERNAL','++D=BOOL\tN=Box_PackCount_Valid\tG=VAR\tConst=0\tRO=0\tCom=箱内移動許可：個数5～80かつ5の倍数\r\n+GN=VAR_EXTERNAL',1)
 # 既存配列の空き要素2/4およびTON[3]だけを利用する。
 old_program='\n'.join(json.dumps(s['rows']) for s in d['sections'])
 for axis in [2,3,4,5]:
  assert not re.search(r'RCON2_'+str(axis)+r'_M\[(?:2|3|4|5)\]',old_program)
  assert f'RCON2_{axis}_TON[3]' not in old_program
  assert rd[f'RCON2_{axis}_TON']['D']=='ARRAY[0..99] OF TON'
 for name in ['AutoMode','Pause','M9999']:
  if name not in rd:
   assert name in gd
   rt+=f"++D={gd[name]['D']}\tN={name}\tG=VAR_EXTERNAL\tConst=0\tRO=0\tCom=既存の運転状態参照\r\n"
 if rt!=z.read(localrcon).decode('utf-8-sig'):patches[localrcon]=encode(z.read(localrcon),rt)
 patches[localbox]=encode(z.read(localbox),bt)
 for name,newrows in [('BoxPacking_箱詰め',box),('RCON_IAI',rcon),(output_name,output)]:
  part=sections[name]['part'];orig=z.read(part)
  patches[part]=encode(orig,''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in newrows))
 out=io.BytesIO()
 with ZipFile(out,'w') as w:
  w.comment=z.comment
  for info in z.infolist():w.writestr(copy(info),patches.get(info.filename,z.read(info.filename)))
 data=out.getvalue()
 with ZipFile(io.BytesIO(data)) as w:
  assert w.testzip() is None and w.namelist()==z.namelist()
  changed=[n for n in z.namelist() if z.read(n)!=w.read(n)];assert set(changed)==set(patches)
 assert src.read_bytes()==raw
 with stage.open('wb') as f:f.write(data)
 report={'source':str(src),'staged':str(stage),'output':str(dest),'archive':str(archive),'source_sha256':d['sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),'changed_parts':changed,'preserved_parts':len(z.namelist())-len(changed),'box_part':sections['BoxPacking_箱詰め']['part'],'rcon_part':sections['RCON_IAI']['part'],'output_part':sections[output_name]['part'],'output_rows':len(output),'output_changed_rows':output_changed,'box_rows':len(box),'rcon_rows':len(rcon),'native_validation':None,'independent_audit':None,'published':False,'archived':False}
 (b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
