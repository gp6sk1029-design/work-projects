"""行別対応表で、追加28を保持した旧工程の繰下げだけを検証する。"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
P=Path(__file__).resolve().parent/'verification.json';r=json.loads(P.read_text(encoding='utf-8-sig'))
PAT=re.compile(r'ST7_A_Dis2_M\[(\d+)\]');MAP={28:29,29:30,30:31,31:32,32:33}
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def fields(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
with zipfile.ZipFile(r['source']) as a,zipfile.ZipFile(r['staged']) as b:
    changed=[n for n in a.namelist() if a.read(n)!=b.read(n)];assert set(changed)==set(r['changed_entries'])
    target=next(n for n in r['ladder_counts'] if n.endswith('1c62506a-fffa-4120-bf30-bcfd518c76f9.xml'))
    refcount=0;coils=collections.Counter()
    for n in r['ladder_counts']:
        old=[json.loads(l) for l in a.read(n).decode('utf-8-sig').splitlines() if l.strip()]
        new=[json.loads(l) for l in b.read(n).decode('utf-8-sig').splitlines() if l.strip()]
        expected=copy.deepcopy(old)
        for i,row in enumerate(expected):
            if n!=target or i<20:continue
            for node in walk(row):
                m=PAT.fullmatch(node.get('Var',''))
                if m and int(m[1]) in MAP:node['Var']=f'ST7_A_Dis2_M[{MAP[int(m[1])]}]';refcount+=1
        assert new==expected
        for node in walk(new):
            m=PAT.fullmatch(node.get('Var',''))
            if m and node.get('__type')=='ST':coils[int(m[1])]+=1
        if n==target:
            assert new[:20]==old[:20]
            assert new[20]['CLs'][0]['Var']=='ST7_A_Dis2_M[27]'
            for i,ix in {19:28,20:29,21:30,22:31,23:32,24:33}.items():
                assert [int(PAT.fullmatch(x['Var'])[1]) for x in walk(new[i]) if x.get('__type')=='ST' and PAT.fullmatch(x.get('Var',''))]==[ix]
    assert coils=={i:1 for i in range(1,34)} and refcount==14
    for n in r['comments_by_entry']:
        aa=a.read(n).decode('utf-8-sig').splitlines();bb=b.read(n).decode('utf-8-sig').splitlines();assert len(aa)==len(bb)
        for al,bl in zip(aa,bb):
            if al==bl:continue
            ap,bp=fields(al),fields(bl);assert ap['N']==bp['N']=='ST7_A_Dis2_M'
            ac={int(e.get('EK')[1:-1]):e.get('C') for e in ET.fromstring(ap.pop('EC'))}
            bc={int(e.get('EK')[1:-1]):e.get('C') for e in ET.fromstring(bp.pop('EC'))}
            assert ap==bp
            exp={MAP.get(i,i):c for i,c in ac.items()};exp[28]='排出チャック戻／ワーク解放';assert exp==bc
assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==r['source_sha256']
r['independent_audit']={'reference_changes':14,'coils_1_to_33_unique':True,'new_rung_19_and_prior_data_unchanged':True,
                         'only_requested_indices_and_comments_changed':True,'unchanged_entries':r['entries']-len(changed),'source_unchanged':True}
P.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r['independent_audit'],ensure_ascii=False))
