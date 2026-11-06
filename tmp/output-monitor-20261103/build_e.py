"""Outputの異常監視Auto接点を対応する駆動回路と揃えてE版を作成する。"""
from pathlib import Path
from copy import deepcopy,copy
import zipfile,json,re,hashlib,io,sys,csv,time
sys.stdout.reconfigure(encoding='utf-8')
start=time.monotonic();b=Path(__file__).parent
info=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
src=Path(info['source']);raw=src.read_bytes()
assert hashlib.sha256(raw).hexdigest()==info['sha256'],'D版が外部更新されたため停止'
dest=src.with_name(src.name.replace('20261103D.smc2','20261103E.smc2'))
assert dest!=src and not dest.exists(),'E版の保存先が使用済み'
def objects(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from objects(v)
 elif isinstance(x,list):
  for v in x:yield from objects(v)
def autos(row):return [e for e in row['CLs'] if e.get('__type')=='LD' and re.fullmatch(r'.+_Auto\[\d+\]',e.get('Var',''))]
changes=[];added_count=0;replace_count=0
with zipfile.ZipFile(io.BytesIO(raw)) as zin:
 assert zin.testzip() is None
 original=zin.read(info['part']);lines=original.decode('utf-8-sig').splitlines(keepends=True)
 before=[json.loads(l) for l in lines];after=deepcopy(before)
 for pair in info['pairs']:
  if not pair['missing'] and not pair['extra']:continue
  rownum=pair['monitor_row'];row=after[rownum];old=deepcopy(row)
  expected=pair['expected'];existing=autos(row);replacements=[];newvars=[]
  if pair['extra']:
   assert len(existing)==1 and len(pair['extra'])==1 and expected[0] not in pair['existing']
   replacements=[(existing[0]['Var'],expected[0])];existing[0]['Var']=expected[0];replace_count+=1
  missing=[v for v in expected if v not in {e['Var'] for e in existing}]
  if missing:
   count=len(existing);assert count>=1
   assert [e.get('Y',0) for e in existing]==list(range(count))
   assert all(e.get('X',0)==0 and not e.get('Not',False) for e in existing)
   assert not any(e.get('X',0)==0 and e.get('Y',0)>=count for e in row['CLs']),'追加枝と競合する既存接点あり'
   maximum=max([row['LRI'],row['RRI']]+[e.get('Ix',0) for e in objects(row)])
   position=row['CLs'].index(existing[-1])+1
   for j,v in enumerate(missing):
    maximum+=1;contact={'__type':'LD','Ix':maximum,'Var':v,'Y':count+j}
    row['CLs'].insert(position+j,contact);newvars.append(v);added_count+=1
   if count==1:
    assert not any(v.get('X',0)==1 and v.get('Y',0)==0 for v in row.get('VLs',[]))
    maximum+=1;merge=maximum
   else:
    current=[v for v in row.get('VLs',[]) if v.get('X',0)==1 and v.get('Y',0)<count-1]
    assert {v.get('Y',0) for v in current}==set(range(count-1)) and len({v['Ix'] for v in current})==1
    merge=current[0]['Ix']
   for y in range(count-1,count+len(missing)-1):
    v={'Ix':merge,'X':1}
    if y:v['Y']=y
    row.setdefault('VLs',[]).append(v)
   assert {v.get('Y',0) for v in row['VLs'] if v['Ix']==merge}==set(range(count+len(missing)-1))
  assert [e['Var'] for e in autos(row)]==expected
  # 追加したAuto接点と変数名修正を除けば、元の命令と座標がそのまま残る。
  restored=deepcopy(row)
  restored['CLs']=[e for e in restored['CLs'] if e.get('Var') not in newvars]
  for oldname,newname in replacements:
   found=[e for e in restored['CLs'] if e.get('__type')=='LD' and e.get('Var')==newname];assert len(found)==1;found[0]['Var']=oldname
  assert restored['CLs']==old['CLs']
  assert {k:v for k,v in row.items() if k not in ['CLs','VLs']}=={k:v for k,v in old.items() if k not in ['CLs','VLs']}
  ids=[v['Ix'] for e in row['CLs'] for v in objects(e) if 'Ix' in v]
  assert len(ids)==len(set(ids)) and not set(ids)&({row['LRI'],row['RRI']}|{v['Ix'] for v in row.get('VLs',[])})
  changes.append({'駆動行':pair['drive_row'],'異常監視行':rownum,'出力区分':pair['group'],'出力番号':pair['index'],'修正前Auto':pair['existing'],'修正後Auto':expected,'追加接点':newvars,'変数修正':replacements})
 assert len(changes)==23 and added_count==22 and replace_count==4
 for pair in info['pairs']:assert [e['Var'] for e in autos(after[pair['monitor_row']])]==pair['expected']
 changed_rows={r['異常監視行'] for r in changes}
 out=[]
 for i,(r1,r2,line) in enumerate(zip(before,after,lines)):
  if i not in changed_rows:assert r1==r2;out.append(line)
  else:
   ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
   out.append(json.dumps(r2,ensure_ascii=False,separators=(',',':'))+ending)
 patch=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8')
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w') as zout:
  zout.comment=zin.comment
  for e in zin.infolist():zout.writestr(copy(e),patch if e.filename==info['part'] else zin.read(e.filename))
 result=buf.getvalue()
 with zipfile.ZipFile(io.BytesIO(result)) as z:
  assert z.testzip() is None and z.namelist()==zin.namelist()
  assert [n for n in zin.namelist() if zin.read(n)!=z.read(n)]==[info['part']]
  assert [json.loads(l) for l in z.read(info['part']).decode('utf-8-sig').splitlines()]==after
 assert src.read_bytes()==raw
 with dest.open('xb') as f:f.write(result)
 assert dest.read_bytes()==result
 report={'source':str(src),'output':str(dest),'source_sha256':info['sha256'],'output_sha256':hashlib.sha256(result).hexdigest(),'target':info['part'],'checked_pairs':100,'changed_monitor_rows':23,'added_contacts':added_count,'replaced_wrong_contacts':replace_count,'remaining_mismatches':0,'preserved_parts':len(zin.namelist())-1,'ZIP_CRC':'正常','native_Sysmac_build':'未実施','seconds':round(time.monotonic()-start,3),'changes':changes}
 (b/'build_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 with (b/'異常監視接点変更一覧.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(changes[0]));w.writeheader();w.writerows(changes)
 print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False))
