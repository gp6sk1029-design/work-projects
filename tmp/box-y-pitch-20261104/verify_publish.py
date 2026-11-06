"""保存されたXY式・宣言・差分を読み直してから同名D版へ反映する。"""
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from lxml import etree as E
import hashlib,json,re,os

b=Path(__file__).parent
m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
src=Path(m['source']);stage=Path(m['staged']);backup=Path(m['backup'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
assert backup.read_bytes()==src.read_bytes()
assert m['native_validation']['box_section']=='TOTAL=28 PARSE_FAIL=0 MODEL_FAIL=0'
assert len(m['native_validation']['variables'])==2

def fields(text):
 return [dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p) for line in text.splitlines() if line.startswith('++D=')]

with ZipFile(backup) as a,ZipFile(stage) as z:
 assert z.testzip() is None and a.namelist()==z.namelist()
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==m['changed_parts']
 beforelines=a.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 afterlines=z.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 assert len(beforelines)==len(afterlines)==28 and beforelines[:27]==afterlines[:27]
 old=json.loads(beforelines[27]);new=json.loads(afterlines[27]);restored=deepcopy(new)
 oldist=next(c for c in old['CLs'] if c['__type']=='IST')
 ist=next(c for c in restored['CLs'] if c['__type']=='IST');st=ist['TXT']
 assert st.startswith(oldist['TXT']+'\r\n'),'X軸の既存STが変更されている'
 ist['TXT']=oldist['TXT'];restored['CMT']=old['CMT'];assert restored==old
 assert Path(m['ST']).read_bytes()==b'\xef\xbb\xbf'+st.encode('utf-8')
 for part,scope in [(m['localpart'],'VAR_EXTERNAL'),(m['globalpart'],'VAR_GLOBAL')]:
  bef=fields(a.read(part).decode('utf-8-sig'));aft=fields(z.read(part).decode('utf-8-sig'))
  added=[d for d in aft if d['N']==m['pitch']]
  assert len(aft)==len(bef)+1 and len(added)==1
  assert added[0]['D']=='LREAL' and added[0]['G']==scope and added[0]['Const']==added[0]['RO']=='0'
  assert len({d['N'].casefold() for d in aft})==len(aft)
  previous={d['N']:d for d in bef}
  for d in aft:
   if d['N']==m['pitch']:continue
   if d['N']=='HMI_RCON2_3_OUT_TargetPos':
    oldec=E.fromstring(previous[d['N']]['EC'].encode());newec=E.fromstring(d['EC'].encode())
    addedec=[e for e in newec if e.get('EK')=='[3]'];assert len(addedec)==1;newec.remove(addedec[0])
    assert E.tostring(oldec)==E.tostring(newec)
    dd=dict(d);dd['EC']=previous[d['N']]['EC'];assert dd==previous[d['N']]
   else:assert d==previous[d['N']]
 executable=re.sub(r'//[^\n]*','',st)
 assert re.findall(r'(\w+)\s*:=',executable)==['RCON2_2_OUT_TargetPos_mm']*4+['RCON2_3_OUT_TargetPos_mm']*4
 axis_blocks={}
 for axis in [2,3]:
  blocks=re.findall(r'(?:IF|ELSIF)\s+((?:\(Box_Total_CT = INT#\d+\)\s*(?:OR\s*)?)+)THEN\s+RCON2_'+str(axis)+r'_OUT_TargetPos_mm\s*:=\s*(.*?);',executable,re.S)
  assert len(blocks)==4
  counts=[int(n) for cond,_ in blocks for n in re.findall(r'INT#(\d+)',cond)]
  assert sorted(counts)==list(range(5,81,5)) and len(set(counts))==16
  assert all(not any(c in map(int,re.findall(r'INT#(\d+)',cond)) for cond,_ in blocks) for c in [-5,0,1,4,6,79,81,85])
  axis_blocks[axis]=blocks
 checked=0;positions=[]
 for xs,ys,xp,yp in [(100.,200.,12.5,20.),(100.,200.,-12.5,-20.),(100.,200.,12.5,-20.),(100.,200.,0.,0.)]:
  for number,count in enumerate(range(5,81,5)):
   pair=[]
   for axis,start,pitch in [(2,xs,xp),(3,ys,yp)]:
    exprs=[expr for cond,expr in axis_blocks[axis] if count in map(int,re.findall(r'INT#(\d+)',cond))];assert len(exprs)==1
    expr=exprs[0].replace(f'HMI_RCON2_{axis}_OUT_TargetPos[3]',repr(start)).replace('HMI_Box_'+('X' if axis==2 else 'Y')+'_Pitch_mm',f'({pitch})').replace('LREAL#','')
    assert re.fullmatch(r'[\d\s.()+*\-]+',expr)
    result=eval('('+expr+')',{'__builtins__':{}},{})
    expected=start+(number%4 if axis==2 else number//4)*pitch
    assert result==expected;pair.append(result);checked+=1
   if xp==12.5 and yp==20.:positions.append(tuple(pair))
 assert len(positions)==len(set(positions))==16

data=stage.read_bytes();assert hashlib.sha256(data).hexdigest()==m['output_sha256']
temp=src.with_name(src.name+'.codex-y-tmp');assert not temp.exists()
with temp.open('xb') as f:f.write(data)
assert temp.read_bytes()==data
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
os.replace(temp,src);assert src.read_bytes()==data
m['published']=True
m['independent_verification']={'coordinate_cases':checked,'unique_XY_positions':16,'invalid_counts_tested_per_axis':8,'X_ST_unchanged':True,'rung_topology_unchanged':True,'other_parts_identical':207,'backup_verified':True,'same_name_D_overwritten':True}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(src),'pitch':m['pitch'],'verification':m['independent_verification'],'source_sha256':m['source_sha256'],'output_sha256':m['output_sha256']},ensure_ascii=False))
