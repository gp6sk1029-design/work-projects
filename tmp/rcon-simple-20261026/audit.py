"""保存済みZIPを原本と再照合し、完了コイルと参照の対応を独立検証する。"""
from pathlib import Path
import copy,hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).resolve().parent
report=json.loads((base/'verification.json').read_text(encoding='utf-8-sig'))
pattern=re.compile(r'(?<![A-Za-z0-9_])RCON1_([1-6])_M\[\s*2\s*\]')
def mapped(x):return pattern.sub(lambda m:f'RCON1_{m[1]}_MoveDone',x)
def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from walk(v)
    elif isinstance(x,list):
        for v in x:yield from walk(v)
def parse(raw):return raw.decode('utf-8-sig')
def fields(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
coils={i:[] for i in range(1,7)};refs={i:0 for i in coils};rows_total=0;new_names=set()
with zipfile.ZipFile(report['source']) as source,zipfile.ZipFile(report['staged']) as dest:
    assert source.namelist()==dest.namelist() and dest.testzip() is None
    changed=[n for n in source.namelist() if source.read(n)!=dest.read(n)]
    assert set(changed)==set(report['changed_entries'])
    for n in source.namelist():
        a,b=source.read(n),dest.read(n)
        if n in report['ladder_counts']:
            old=[json.loads(l) for l in parse(a).splitlines() if l.strip()]
            new=[json.loads(l) for l in parse(b).splitlines() if l.strip()]
            assert len(old)==len(new);rows_total+=len(new)
            for i,(ar,br) in enumerate(zip(old,new)):
                ar=copy.deepcopy(ar);br=copy.deepcopy(br);ar.pop('CMT',None);br.pop('CMT',None)
                for node in walk(ar):
                    for key in ('Var','TXT'):
                        if isinstance(node.get(key),str):node[key]=mapped(node[key])
                assert ar==br,(n,i)
                for node in walk(br):
                    match=re.fullmatch('RCON1_([1-6])_MoveDone',node.get('Var',''))
                    if match:
                        axis=int(match[1]);refs[axis]+=1
                        if node.get('__type')=='ST':coils[axis].append((n,i))
        try:t=parse(b)
        except UnicodeError:continue
        assert not pattern.search(t),n
        if t.startswith('[SLWD'):
            for line in t.splitlines():
                if not line.startswith('++D='):continue
                f=fields(line);name=f['N']
                if re.fullmatch('RCON1_[1-6]_MoveDone',name):
                    assert f['D']=='BOOL' and f['Const']=='0' and f['RO']=='0' and 'AT' not in f
                    if f['G']=='VAR_GLOBAL':new_names.add(name)
        if n.endswith('7b1666c7-ee97-4210-81b2-fed5a6172074.xml'):
            rs=[json.loads(l) for l in t.splitlines() if l.strip()]
            for axis in range(1,7):
                group=rs[(axis-1)*40:axis*40]
                assert group[0]['CMT'].startswith('#')
                assert all('RCON1_' not in r['CMT'] for r in group[1:])
                assert group[39]['CMT']=='動作完了（100ms保持）'
                # 元の完了コイルと保持接点、TON入力の結線が同じであることは上の全行比較で保証。
                assert any(node.get('Var')==f'RCON1_{axis}_MoveDone' for node in walk(group[39]))
    assert len(new_names)==6
    assert refs=={1:6,2:3,3:3,4:3,5:3,6:3},refs
    # ラダーのコイル型名はメーカー保存形式から確定して検証する。
    node_types={}
    for n in report['ladder_counts']:
        for row in [json.loads(l) for l in parse(dest.read(n)).splitlines() if l.strip()]:
            for node in walk(row):
                if re.fullmatch('RCON1_[1-6]_MoveDone',node.get('Var','')):node_types[node.get('__type')]=node_types.get(node.get('__type'),0)+1
    print('MOVEdone node types',node_types)
    assert node_types=={'LD':15,'ST':6},node_types
    assert all(len(coils[i])==1 for i in coils),coils
assert hashlib.sha256(Path(report['source']).read_bytes()).hexdigest()==report['source_sha256']
report['independent_audit']={'sections':len(report['ladder_counts']),'rows':rows_total,'new_done_coils':6,
                             'done_reference_count':refs,'unmodified_entries':report['entries']-len(changed),
                             'all_ladders_equal_except_comments_and_requested_rename':True,'source_unchanged':True}
(base/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report['independent_audit'],ensure_ascii=False))
