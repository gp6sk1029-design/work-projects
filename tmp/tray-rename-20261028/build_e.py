"""トレイ01/02をNG1/NG2へ改称する。配線・割付・動作条件は変更しない。"""
from pathlib import Path
import collections,hashlib,json,re,shutil,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
DATA=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
SOURCE=Path(DATA['source']);DEST=SOURCE.with_name(SOURCE.name.replace('20261029D','20261029E'));STAGED=BASE/DEST.name
REPORT=BASE/'verification.json'
MAP={}
for prefix in ('In_Sen_','TimerQ_In_Sen_','Timer_In_Sen_'):
    for number,ng in [('01','1'),('02','2')]:
        for side in 'AB':
            for suffix in ('Full','Full_Warn'):
                MAP[f'{prefix}NG1_Tray_{number}_{side}_{suffix}']=f'{prefix}NG{ng}_Tray_{side}_{suffix}'
PAT=re.compile(r'(?<![A-Za-z0-9_])(?:'+'|'.join(map(re.escape,sorted(MAP,key=len,reverse=True)))+r')(?![A-Za-z0-9_])')
def rename(t):return PAT.sub(lambda m:MAP[m[0]],t)
def comments(t):
    t=t.replace('NG1トレイ1','NG1トレイ').replace('NG1トレイ2','NG2トレイ')
    # 既存HMIラベルも、側の表記を先頭へ揃える。
    t=re.sub(r'(NG[12]トレイ)([AB]\([左右]側\))',r'\2 \1',t)
    return re.sub(r'(NG[12]トレイ満杯)(?!停止|警告)',r'\1停止',t)
def transform(t):return comments(rename(t))
def fields(l):return dict(x.split('=',1) for x in l[2:].split('\t') if '=' in x)
def decls(t):return [fields(l) for l in t.splitlines() if l.startswith('++D=')]
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)

def build():
    assert not DEST.exists() and not STAGED.exists(),'既存E版を上書きしません'
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==DATA['sha256']
    names={p['N'] for table in DATA['tables'].values() for p in table.values()}
    assert set(MAP)<=names
    assert not set(MAP.values())&names,'変更先の変数名が既に存在します'
    with zipfile.ZipFile(SOURCE) as z:
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();zc=z.comment
    changes={};renamed_decls=[];refs=collections.Counter();comment_count=0
    for n,t in DATA['texts'].items():
        after=transform(t)
        if t.startswith('[SLWD'):
            aa=decls(t);bb=decls(after)
            assert len(aa)==len(bb)
            assert len({p['N'].lower() for p in bb})==len(bb),'宣言名重複'
            for a,b in zip(aa,bb):
                assert {k:v for k,v in a.items() if k not in ('N','Com','EC')}=={k:v for k,v in b.items() if k not in ('N','Com','EC')},'属性を変更しない'
                assert b['N']==MAP.get(a['N'],a['N'])
                if a['N'] in MAP:renamed_decls.append({'entry':n,'old':a['N'],'new':b['N'],'type':a['D'],'group':a['G']})
                if a.get('Com')!=b.get('Com'):comment_count+=1
        if n in DATA['ladder_counts']:
            aa=[json.loads(l) for l in t.splitlines() if l.strip()]
            bb=[json.loads(l) for l in after.splitlines() if l.strip()]
            assert len(aa)==len(bb)==DATA['ladder_counts'][n]
            # 指定の名称・既存コメント以外は全て同一。
            assert json.loads(transform(json.dumps(aa,ensure_ascii=False)))==bb
            for row in aa:
                if comments(row.get('CMT',''))!=row.get('CMT',''):comment_count+=1
                for node in walk(row):
                    for key in ('Var','TXT'):
                        if isinstance(node.get(key),str):refs.update(m[0] for m in PAT.finditer(node[key]))
        if t.lstrip().startswith('<'):
            try:a=ET.fromstring(t);b=ET.fromstring(after)
            except ET.ParseError:continue
            assert len(list(a.iter()))==len(list(b.iter()))
            for ae,be in zip(a.iter(),b.iter()):
                assert ae.tag==be.tag
                assert {k:transform(v) for k,v in ae.attrib.items()}==be.attrib
                assert transform(ae.text or '')==(be.text or '')
                if ae.attrib.get('Comment')!=be.attrib.get('Comment') or (ae.text!=be.text and 'NG1トレイ' in (ae.text or '')):comment_count+=1
        if after!=t:changes[n]=after
    assert len(refs)==24,'タイマーを含む全24名称のラダー参照を確認'
    assert not any(n.endswith(('.dat','.oem')) for n in changes)
    for n,raw in original.items():
        if n not in DATA['texts']:
            assert not any(old.encode(enc) in raw for old in MAP for enc in ('utf-8','utf-16-le')),('未対応形式に旧名称あり',n)
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=zc
        for info in infos:
            raw=original[info.filename]
            if info.filename in changes:raw=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changes[info.filename].encode('utf-8')
            z.writestr(info,raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        for n,raw in original.items():
            if n not in changes:assert z.read(n)==raw
            else:
                saved=z.read(n).decode('utf-8-sig')
                assert saved==transform(raw.decode('utf-8-sig'))
                assert not PAT.search(saved)
                assert not re.search('NG1トレイ[12]',saved)
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':DATA['sha256'],
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'rename_map':MAP,'entries':len(original),'changed_entries':list(changes),
            'declaration_renames':renamed_decls,'ladder_reference_counts':dict(refs),'comment_change_count':comment_count,
            'ladder_counts':DATA['ladder_counts'],'physical_io_and_logic_preserved':True,'native_validation':None,'native_variables':None,
            'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['rename_map','declaration_renames','ladder_counts','ladder_reference_counts']},ensure_ascii=False,indent=2))
    print('名称24種類、宣言',len(renamed_decls),'ラダー参照',sum(refs.values()),'コメント',comment_count)

def publish():
    r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert r['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in x for x in r['native_validation'].values())
    assert r['native_variables'] and r['independent_audit']
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
    with STAGED.open('rb') as a,DEST.open('xb') as b:shutil.copyfileobj(a,b)
    assert hashlib.sha256(DEST.read_bytes()).hexdigest()==r['output_sha256']
    r['published']=True;REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)
if __name__=='__main__':publish() if '--publish' in sys.argv else build()
