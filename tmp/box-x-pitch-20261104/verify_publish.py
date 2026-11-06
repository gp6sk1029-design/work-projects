"""保存内容を検算し、検査を通過したD版を同名へ上書きする。"""
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from lxml import etree as E
import hashlib,json,re,os

b=Path(__file__).parent
m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
src=Path(m['source']);backup=Path(m['backup']);stage=Path(m['staged'])
assert hashlib.sha256(backup.read_bytes()).hexdigest()==m['source_sha256']
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256'],'編集途中でD版が変わったため停止'
assert m['native_validation']['box_section']=='TOTAL=28 PARSE_FAIL=0 MODEL_FAIL=0'
assert len(m['native_validation']['variables'])==2

def fields(text):
 return [dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p) for line in text.splitlines() if line.startswith('++D=')]

with ZipFile(backup) as a,ZipFile(stage) as z:
 assert z.testzip() is None and a.namelist()==z.namelist()
 assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==m['changed_parts']
 al=a.read(m['target']).decode('utf-8-sig').splitlines(keepends=True);bl=z.read(m['target']).decode('utf-8-sig').splitlines(keepends=True)
 assert al[:27]==bl[:27] and len(al)==len(bl)==28
 old=json.loads(al[27]);new=json.loads(bl[27]);restored=deepcopy(new)
 oldist=next(c for c in old['CLs'] if c['__type']=='IST')
 ist=next(c for c in restored['CLs'] if c['__type']=='IST')
 assert ist['TXT']==oldist['TXT'].replace('HMI_RCON2_2_OUT_TargetPos[4]',m['pitch'])
 st=ist['TXT'];ist['TXT']=oldist['TXT'];restored['CMT']=old.get('CMT');assert restored==old
 assert Path(m['ST']).read_bytes()==b'\xef\xbb\xbf'+st.encode('utf-8')
 assert 'HMI_RCON2_2_OUT_TargetPos[4]' not in st
 for part,scope in [(m['localpart'],'VAR_EXTERNAL'),(m['globalpart'],'VAR_GLOBAL')]:
  bef=fields(a.read(part).decode('utf-8-sig'));aft=fields(z.read(part).decode('utf-8-sig'))
  added=[d for d in aft if d['N']==m['pitch']]
  assert len(aft)==len(bef)+1 and len(added)==1 and added[0]['D']=='LREAL' and added[0]['G']==scope
  assert len({d['N'].casefold() for d in aft})==len(aft)
  previous={d['N']:d for d in bef}
  for d in aft:
   if d['N']==m['pitch']:continue
   if d['N']=='HMI_RCON2_2_OUT_TargetPos':
    oldec=E.fromstring(previous[d['N']]['EC'].encode());newec=E.fromstring(d['EC'].encode())
    removed=[e for e in oldec if e.get('EK')=='[4]'];assert len(removed)==1;oldec.remove(removed[0])
    assert E.tostring(oldec)==E.tostring(newec)
    dd=dict(d);dd['EC']=previous[d['N']]['EC'];assert dd==previous[d['N']]
   else:assert d==previous[d['N']]
 executable=re.sub(r'//[^\n]*','',st)
 assert re.findall(r'(\w+)\s*:=',executable)==['RCON2_2_OUT_TargetPos_mm']*4
 blocks=re.findall(r'(?:IF|ELSIF)\s+((?:\(Box_Total_CT = INT#\d+\)\s*(?:OR\s*)?)+)THEN\s+RCON2_2_OUT_TargetPos_mm\s*:=\s*(.*?);',executable,re.S)
 assert len(blocks)==4
 counts=[int(n) for cond,_ in blocks for n in re.findall(r'INT#(\d+)',cond)]
 assert sorted(counts)==list(range(5,81,5)) and len(set(counts))==16
 checked=0
 for start,pitch in [(100.,12.5),(100.,-12.5),(100.,0.)]:
  for index,count in enumerate(range(5,81,5)):
   expr=next(expr for cond,expr in blocks if count in map(int,re.findall(r'INT#(\d+)',cond)))
   expr=expr.replace('HMI_RCON2_2_OUT_TargetPos[3]',repr(start)).replace(m['pitch'],f'({pitch})').replace('LREAL#','')
   assert re.fullmatch(r'[\d\s.()+*\-]+',expr)
   assert eval('('+expr+')',{'__builtins__':{}},{})==start+(index%4)*pitch;checked+=1

# 別名の一時ファイルを同じデスクトップ内に作り、検算済み内容で置換する。
data=stage.read_bytes();assert hashlib.sha256(data).hexdigest()==m['output_sha256']
replacement=src.with_name(src.name+'.codex-pitch-tmp')
assert not replacement.exists()
with replacement.open('xb') as f:f.write(data)
assert replacement.read_bytes()==data
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
os.replace(replacement,src)
assert src.read_bytes()==data
m['published']=True
m['independent_verification']={'coordinate_cases':checked,'counter_positions':16,'other_parts_identical':207,'old_rung_topology_identical':True,'new_variable_declarations':2,'existing_declarations_preserved_except_old_pitch_comment':True,'backup_verified':True,'same_name_D_overwritten':True}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(src),'pitch':m['pitch'],'type':'LREAL','verification':m['independent_verification']},ensure_ascii=False))
