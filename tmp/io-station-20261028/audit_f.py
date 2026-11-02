"""原本との独立比較でST追記以外の変更を検出する。"""
from pathlib import Path
import copy,hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent;RP=BASE/'verification.json';r=json.loads(RP.read_text(encoding='utf-8-sig'))
def fields(l):return dict(x.split('=',1) for x in l[2:].split('\t') if '=' in x)
def comments_only(a,b):
    if a==b:return
    assert 'ST' not in a or not re.search(r'ST\d',a),'既存ST記載は変更しない'
    assert re.findall(r'【[XY][0-9A-F]+】',a)==re.findall(r'【[XY][0-9A-F]+】',b),'アドレス表記の変化'
    # 複数信号を含む行コメントは、共通信号の部分だけを個別に不変確認する。
    for segment in re.findall(r'【[XY][0-9A-F]+】[^【\r\n]*',a):
        if re.search(r'アキューム|コンテナ|段バラシ|箱入れ|箱詰|受渡|受け渡|非常停止|ドア|エア圧|シグナル|プレス',segment):
            assert segment in b,('共通信号の変化',segment)
    stripped=re.sub(r'ST[0-7](?!\d)','',b)
    norm=lambda c:re.sub(r'\s+','',c)
    assert norm(a)==norm(stripped),('ST追記以外の説明変化',a,b)
    assert re.search(r'ST[0-7]',b)

def validate_xml(a,b):
    aa=ET.fromstring(a);bb=ET.fromstring(b)
    assert len(list(aa.iter()))==len(list(bb.iter()))
    for x,y in zip(aa.iter(),bb.iter()):
        assert x.tag==y.tag and set(x.attrib)==set(y.attrib)
        for k in x.attrib:
            if k.rsplit('}',1)[-1] in ('C','Com','Comment','CMT'):comments_only(x.attrib[k],y.attrib[k])
            else:assert x.attrib[k]==y.attrib[k]
        if x.tag.rsplit('}',1)[-1] in ('Comment','Com','CMT','Text'):comments_only(x.text or '',y.text or '')
        else:assert x.text==y.text
        assert x.tail==y.tail

global_before={};global_after={};changed=[];atcount=0;rowcount=0
with zipfile.ZipFile(r['source']) as a,zipfile.ZipFile(r['staged']) as b:
    assert a.namelist()==b.namelist()
    for n in a.namelist():
        av=a.read(n);bv=b.read(n)
        if av!=bv:changed.append(n)
        if n.endswith(('.dat','.oem','.NexBuildVerifierGroup')):assert av==bv
        try:at=av.decode('utf-8-sig');bt=bv.decode('utf-8-sig')
        except UnicodeError:assert av==bv;continue
        if at.startswith('[SLWD'):
            old=[fields(l) for l in at.splitlines() if l.startswith('++D=')]
            new=[fields(l) for l in bt.splitlines() if l.startswith('++D=')]
            assert len(old)==len(new)
            for x,y in zip(old,new):
                assert set(x)==set(y)
                for k in x:
                    if k=='Com':comments_only(x[k],y[k])
                    elif k=='EC':validate_xml(x[k],y[k])
                    else:assert x[k]==y[k],(x['N'],k)
                if x.get('AT'):assert x['AT']==y['AT'];atcount+=1
                if x['G']=='VAR_GLOBAL':global_before[x['N']]=x;global_after[y['N']]=y
        elif n in r['ladder_counts']:
            aa=[json.loads(l) for l in at.splitlines() if l.strip()];bb=[json.loads(l) for l in bt.splitlines() if l.strip()]
            assert len(aa)==len(bb)==r['ladder_counts'][n];rowcount+=len(aa)
            for x,y in zip(aa,bb):
                x=copy.deepcopy(x);y=copy.deepcopy(y)
                comments_only(x.pop('CMT',''),y.pop('CMT',''));assert x==y,'回路条件・命令・結線の差異'
        elif at.lstrip().startswith('<'):validate_xml(at,bt)
        else:assert av==bv,'コメント以外の形式は変更しない'
assert set(changed)==set(r['changed_entries']) and atcount==722
known=0;modified=0;phys=0;excluded=0
for name,p in global_before.items():
    c=p.get('Com','');new=global_after[name].get('Com','')
    if re.search(r'【[XY][0-9A-F]+】',c):
        if re.search(r'ST\d',c):assert c==new;known+=1
        elif c!=new:
            modified+=1;phys+=bool(p.get('AT'))
            m=re.search(r'ワーク位置([0-7])|位置([1-6])ストッパー',c)
            if m:assert f'ST{int(m[1] or m[2])} ' in new
            elif 'NG1' in c:assert 'ST3 ' in new
            elif re.search(r'NG2|ストック|排出チャック|排出フォルダ',c):assert 'ST7 ' in new
            elif '高さ検査' in c:assert 'ST2 ' in new
            elif re.search(r'供給スライド|供給ピックアップ|供給チャック',c):assert 'ST0 ' in new
            elif re.search(r'反転\s*1|反転\s*オリエンタルモータ1',c):assert 'ST4 ' in new
            elif re.search(r'反転\s*2|反転\s*オリエンタルモータ2',c):assert 'ST6 ' in new
            else:raise AssertionError(('所属の根拠なし',name,c))
        else:excluded+=1
assert (known,modified,phys,excluded)==(100,472,164,198),(known,modified,phys,excluded)
assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==r['source_sha256']
r['independent_audit']={'global_comments_added':modified,'physical_io_comments_added':phys,'existing_global_st_comments_preserved':known,
 'excluded_global_comments_preserved':excluded,'all_physical_addresses_preserved':atcount,'rungs_preserved':rowcount,
 'unchanged_entries':r['entries']-len(changed),'only_comments_changed':True,'source_unchanged':True}
RP.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r['independent_audit'],ensure_ascii=False))
