"""保存済みデータに対する独立した対応表で、欠番詰めだけの差分を確認する。"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent;REPORT=BASE/'verification.json'
r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
PAT=re.compile(r'ST7_A_Dis2_M\[(\d+)\]')
MAP={28:27,29:28,30:29,31:30,32:31,33:32}
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def fields(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
with zipfile.ZipFile(r['source']) as a,zipfile.ZipFile(r['staged']) as b:
    assert a.namelist()==b.namelist() and b.testzip() is None
    changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    assert set(changed)==set(r['changed_entries'])
    coils=collections.Counter();refcount=0;blanks=0
    for name in r['ladder_counts']:
        old=[json.loads(l) for l in a.read(name).decode('utf-8-sig').splitlines() if l.strip()]
        new=[json.loads(l) for l in b.read(name).decode('utf-8-sig').splitlines() if l.strip()]
        expected=copy.deepcopy(old)
        for node in walk(expected):
            if 'Var' in node and PAT.fullmatch(node['Var']):
                ix=int(PAT.fullmatch(node['Var'])[1])
                if ix in MAP:node['Var']=f'ST7_A_Dis2_M[{MAP[ix]}]';refcount+=1
        assert expected==new,'添字以外の回路差分'
        for node in walk(new):
            if node.get('__type')=='ST' and PAT.fullmatch(node.get('Var','')):coils[int(PAT.fullmatch(node['Var'])[1])]+=1
        if name.endswith('1c62506a-fffa-4120-bf30-bcfd518c76f9.xml'):
            assert new[:17]==old[:17]
            blanks=sum(node.get('__type')=='LD' and node.get('Var')=='' for node in walk(new))
    assert coils=={i:1 for i in range(1,33)} and refcount==19
    for name in r['comments_by_entry']:
        old=a.read(name).decode('utf-8-sig').splitlines();new=b.read(name).decode('utf-8-sig').splitlines()
        assert len(old)==len(new)
        for al,bl in zip(old,new):
            if al==bl:continue
            ap,bp=fields(al),fields(bl);assert ap['N']==bp['N']=='ST7_A_Dis2_M'
            ae,be=ET.fromstring(ap.pop('EC')),ET.fromstring(bp.pop('EC'));assert ap==bp
            ac={int(e.get('EK')[1:-1]):e.get('C') for e in ae}
            bc={int(e.get('EK')[1:-1]):e.get('C') for e in be}
            assert bc=={MAP.get(i,i):c for i,c in ac.items() if i!=27}
assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==r['source_sha256']
r['independent_audit']={'coils_1_to_32_unique':True,'fixed_reference_changes':refcount,'all_nonindex_ladder_data_identical':True,
                         'existing_comments_up_to_26_preserved_in_each_table':True,'unchanged_entries':r['entries']-len(changed),
                         'blank_contacts_preserved':blanks,'source_unchanged':True}
REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r['independent_audit'],ensure_ascii=False))
