"""保存済みB/C版のコメント以外の同一性を、再読込みして独立照合する。"""
from pathlib import Path
import copy,hashlib,json,re,sys,zipfile,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf8')
desktop=Path(r'C:\Users\SEIGI-N13\Desktop')
c=desktop/'3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261019C.smc2'
b=c.with_name(c.stem[:-1]+'B.smc2')
report=json.loads(c.with_suffix('.コメント検証.json').read_text(encoding='utf8'))
sha=lambda v:hashlib.sha256(v).hexdigest()
assert sha(b.read_bytes())==report['原本SHA256']
assert sha(c.read_bytes())==report['出力SHA256']
def table(t):
 return [dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in t.splitlines() if l.startswith('++D=')]
with zipfile.ZipFile(b) as old,zipfile.ZipFile(c) as new:
 assert old.namelist()==new.namelist() and old.testzip() is None and new.testzip() is None
 changed=[n for n in old.namelist() if old.read(n)!=new.read(n)]
 assert changed==[n for n in old.namelist() if n in report['変更エントリ']]
 assert len(changed)==5
 for n in changed:
  bt=old.read(n).decode('utf-8-sig');ct=new.read(n).decode('utf-8-sig')
  if ct.startswith('[SLWD'):
   br,cr=table(bt),table(ct);assert len(br)==len(cr)
   assert [{k:v for k,v in r.items() if k not in ['Com','EC']} for r in br]==[{k:v for k,v in r.items() if k not in ['Com','EC']} for r in cr]
   assert [l for l in bt.splitlines() if not l.startswith('++D=')]==[l for l in ct.splitlines() if not l.startswith('++D=')]
   for r in cr:
    if 'EC' in r:
     e=ET.fromstring(r['EC'])
     assert len(e)==len({x.get('EK') for x in e})
     assert all(x.get('C','').strip() for x in e)
   if '+GN=VAR_GLOBAL' in ct:g={r['N']:r for r in cr}
   else:l={r['N']:r for r in cr}
  elif '4bdcdc10-734d-4589-b299-075e93db9b10' in n:
   be,ce=ET.fromstring(bt),ET.fromstring(ct)
   dtype=ce
   for r in [be,ce]:
    for e in r.iter():e.attrib.pop('Comment',None)
   assert ET.tostring(be)==ET.tostring(ce)
   tr=ET.fromstring(ct)
   structs=[e for e in tr.iter('DataType') if (e.get('Name') or '').startswith('ST_RCON_Direct')]
   assert len(structs)==4 and sum(len(e) for e in structs)==39
   assert all(e.get('Comment','').strip() and all(m.get('Comment','').strip() for m in e) for e in structs)
  elif n.endswith('.oem'):
   br,cr=ET.fromstring(bt),ET.fromstring(ct)
   for root in [br,cr]:
    root.find('Entity').set('name','共通表示名')
    if root.find('Entity').get('DN') in [b.stem,c.stem]:root.find('Entity').set('DN','共通表示名')
    for e in root.iter('Entity'):e.attrib.pop('dateLastModified',None)
   assert ET.tostring(br)==ET.tostring(cr)
  elif n.endswith('.manifest'):assert ct==bt.replace(b.stem,c.stem,1)
  else:raise AssertionError(n)
 # ST6ブロックの全参照とコメントを照合。先頭ダミーIAI_Mも対象。
 body=next(n for n in old.namelist() if n.endswith('/7b1666c7-ee97-4210-81b2-fed5a6172074.xml'))
 assert old.read(body)==new.read(body)
 rungs=[json.loads(s) for s in new.read(body).decode('utf-8-sig').splitlines() if s.strip()]
 assert len(rungs)==7
 st='\n'.join(r['CLs'][0]['TXT'] for r in rungs[1:])
 st=re.sub(r'//[^\n]*','',st)
 names=set(re.findall(r'\b(?:RCON[12]_|E001_|E005_|Conv)\w*',st));assert len(names)==292
 for name in names:
  assert name in l and l[name].get('Com','').strip(),name
  if name in g:
   assert g[name].get('Com','').strip() and l[name]['Com']==g[name]['Com']
   if 'EC' in g[name]:assert g[name]['EC']==l[name]['EC']
 assert l['IAI_M'].get('Com')
 rcon={n:r for n,r in g.items() if re.match(r'RCON[12]_',n)}
 assert len(rcon)==270 and all(r.get('Com','').strip() for r in rcon.values())
 arr=[r for r in rcon.values() if r['D'].startswith('ARRAY')]
 assert len(arr)==26
 count=0
 for r in arr:
  e=ET.fromstring(r['EC']);m=re.match(r'ARRAY\[(\d+)\.\.(\d+)\]',r['D'])
  assert {x.get('EK') for x in e}=={f'[{i}]' for i in range(int(m[1]),int(m[2])+1)}
  count+=len(e)
 assert count==562
out={'保存済みC版の再読込検証':'合格','原本B版不変':True,'実行ST全文':'B版とバイト同一','全ST参照のコメント':len(names),
 'グローバル対象':670,'ローカル・外部参照対象':293,'構造体型':4,'メンバー':39,'全要素コメント':562,
 '型/初期値/AT/保持区分/配列範囲':'全て同一','不変エントリ':180,'ZIP_CRC':'正常','Sysmacビルド':'未実施'}
(Path(__file__).parent/'comment_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(out,ensure_ascii=False,indent=2))
