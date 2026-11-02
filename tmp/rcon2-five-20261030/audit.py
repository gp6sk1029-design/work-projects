"""生成器から独立して、追加内容・参照・保存範囲を照合する。"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys,zipfile,xml.etree.ElementTree as E
sys.stdout.reconfigure(encoding='utf-8')
B=Path(__file__).resolve().parent
r=json.loads((B/'verification.json').read_text(encoding='utf-8-sig'))
with zipfile.ZipFile(r['source']) as z: before={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(r['staged']) as z:
 assert z.testzip() is None
 after={n:z.read(n) for n in z.namelist()}
assert before.keys()==after.keys()
changed={n for n in before if before[n]!=after[n]}
assert changed==set(r['changed_entries']) and len(changed)==6
def entry(s): return next(n for n in before if n.endswith(s))
def text(raw): return raw.decode('utf-8-sig')
def decls(raw):
 out={}
 for l in text(raw).splitlines():
  if not l.startswith('++D='):continue
  f=dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
  assert f['N'] not in out
  out[f['N']]=f
 return out
def walk(x):
 if isinstance(x,dict):
  yield x
  for y in x.values():yield from walk(y)
 elif isinstance(x,list):
  for y in x:yield from walk(y)
def rows(raw):return [json.loads(l) for l in text(raw).splitlines() if l.strip()]
rn=entry('7b1666c7-ee97-4210-81b2-fed5a6172074.xml')
gn=entry('f07dd06c-505c-431b-b9fc-098949805b4e.xml')
on=entry('a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml')
mn=entry('20a6b651-4c34-401a-965e-db3e18414d5c.xml')
old=rows(before[rn]);new=rows(after[rn]);template=old[203:243]
assert len(old)==249 and len(new)==449
assert new[:243]==old[:243] and new[443:]==old[243:]
for n in r['ladder_counts']:
 if n!=rn:assert before[n]==after[n]
g0,g=decls(before[gn]),decls(after[gn]);o0,o=decls(before[on]),decls(after[on])
added_names=set(g)-set(g0)
assert len(added_names)==130 and added_names==set(r['global_added'])
assert set(g0)<=set(g) and set(o0)<=set(o)
assert len(set(o)-set(o0))==140
at_old={};at_new={}
for n,raw in before.items():
 if not raw.startswith((b'[SLWD',b'\xef\xbb\xbf[SLWD')):continue
 bd,ad=decls(raw),decls(after[n])
 for v,d in bd.items():
  left=d.copy();right=ad[v].copy()
  for k in ('Com','EC'):left.pop(k,None);right.pop(k,None)
  assert left==right,(n,v)
  if d.get('AT'):at_old[n,v]=(d['AT'],d['D'])
 for v,d in ad.items():
  if d.get('AT'):at_new[n,v]=(d['AT'],d['D'])
assert at_old==at_new
guid_old={x['Id'] for rr in old for x in walk(rr) if 'Id' in x}
guids=[];write_counts=collections.Counter();moves=0
for axis,role in r['roles'].items():
 a=int(axis);start=243+(a-1)*40;block=new[start:start+40]
 assert block[0]['CMT'].startswith(f'#RCON2_{a} {role}\r\n')
 assert g[f'RCON2_{a}_M']['Com']==f'#RCON2_{a} {role}'
 assert 'RCON1' not in json.dumps(block)
 expect=copy.deepcopy(template)
 for i,rr in enumerate(expect):
  for x in walk(rr):
   if 'Var' in x:x['Var']=x['Var'].replace('RCON1_6_',f'RCON2_{a}_').replace('RCON1_OUT[6]',f'RCON2_OUT[{a}]').replace('RCON1_IN[6]',f'RCON2_IN[{a}]')
  if i==19:
   rr['CLs'][0]['Var']='P_Off';rr['CLs'][0].pop('Not',None)
 def normalize(rr):
  rr=copy.deepcopy(rr)
  for row in rr:
   row.pop('CMT',None)
   for x in walk(row):x.pop('Id',None)
  return rr
 assert normalize(block)==normalize(expect)
 assert block[5]['CLs'][1]['Var']=='P_Off' and not block[5]['CLs'][1].get('Not',False)
 assert all(x['Var']=='P_Off' and not x.get('Not',False) for x in block[6]['CLs'] if x['__type']=='LD')
 assert block[7]['CLs'][0]['Var']=='Pause[1]' and not block[7]['CLs'][0].get('Not',False)
 assert block[8]['CLs'][0]['Var']=='In_Sw_RESET' and not block[8]['CLs'][0].get('Not',False)
 assert block[19]['CLs'][0]['Var']=='P_Off' and not block[19]['CLs'][0].get('Not',False)
 for i in (0,1,2,3,4,20,21,22,23,24):
  assert block[i]['CLs'][0]['Var']=='P_Off'
  f=next(x for x in block[i]['CLs'] if x.get('Name')=='MOVE')
  vin=next(x['Var'] for x in f['In'] if x.get('Arg')=='In')
  vout=next(x['Var'] for x in f['Out'] if x.get('Arg')=='Out')
  if i<=4:
   assert vin.startswith(f'RCON2_{a}_OUT_') and vout.startswith(f'RCON2_OUT[{a}].')
  else:
   assert vin.startswith(f'RCON2_IN[{a}].') and vout.startswith(f'RCON2_{a}_')
  moves+=1
 for row in block:
  for x in walk(row):
   if 'Id' in x:guids.append(x['Id'])
   v=x.get('Var','')
   if x.get('__type')=='ST':write_counts[v]+=1
   if not v or '#' in v or v in ('P_Off','P_On','TRUE','FALSE'):continue
   base=re.split(r'[.\[]',v,1)[0]
   assert base in o,(a,v)
   m=re.match(r'RCON2_(?:IN|OUT)\[(\d+)\]',v)
   if m:assert int(m[1])==a
 for v in added_names:
  if not v.startswith(f'RCON2_{a}_'):continue
  assert g[v]['Const']==g[v]['RO']=='0'
  assert o[v]['G']=='VAR_EXTERNAL' and o[v]['D'].upper()==g[v]['D'].upper()
  assert o[v]['Const']==o[v]['RO']=='0' and not g[v].get('AT')
 for suffix in ('TON','TOF'):
  d=o[f'RCON2_{a}_{suffix}']
  assert d['G']=='VAR' and d['D']==f'ARRAY[0..99] OF {suffix}'
  assert d['Const']==d['RO']=='0'
 assert not any(v in g for v in (f'RCON2_{a}_Error',f'RCON2_{a}_Error_Clear'))
assert len(guids)==len(set(guids))==15 and not guid_old.intersection(guids)
assert len(write_counts)==150 and set(write_counts.values())=={1}
assert moves==50
for v in ('RCON2_OUT','RCON2_IN'):
 ec={e.get('EK'):e.get('C') for e in E.fromstring(g[v]['EC'])}
 assert all(ec[f'[{a}]']==f'#RCON2_{a} {role}' for a,role in r['roles'].items())
m0={x.get('Name'):x for x in E.fromstring(before[mn]).iter('Variable')}
m1={x.get('Name'):x for x in E.fromstring(after[mn]).iter('Variable')}
assert len(m1)==len(m0)+130
for v,x in m0.items():
 l=x.attrib.copy();rr=m1[v].attrib.copy();l.pop('Comment',None);rr.pop('Comment',None)
 assert l==rr,v
for v in added_names:
 assert m1[v].get('Address')=='new_Controller_0.'+v
 assert all(m1[v].get(k)=='false' for k in ('IsConstant','IsReadOnly','IsReadOnlyNetwork','Retained'))
for n,raw in after.items():
 if n.endswith(('.manifest','.oem')):
  root=E.fromstring(raw)
  val=root.find('Solution').get('solutionName') if n.endswith('.manifest') else root.find('Entity').get('name')
  assert val==Path(r['destination']).stem
assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==r['source_sha256']
r['independent_audit']={'added_rungs':200,'added_writable_globals':130,'added_external_references':130,
 'added_local_timers':10,'move_directions_verified':50,'coil_targets_unique':150,'new_edge_ids_unique':15,
 'physical_at_declarations_unchanged':len(at_old),'all_existing_rungs_and_common_st_unchanged':True,
 'all_other_sections_byte_identical':True,'existing_global_attributes_preserved':True,
 'start_home_brake_P_Off_verified_axes':5,'pause_and_reset_verified_axes':5,'unused_error_or_hmi_helpers_added':0}
(B/'verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r['independent_audit'],ensure_ascii=False,indent=2))
