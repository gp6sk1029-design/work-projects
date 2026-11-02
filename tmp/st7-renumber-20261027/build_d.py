"""承認済みの２重複を解消し、ST7_A_Dis2の接点・コイルと要素コメントを対応させる。"""
from pathlib import Path
import collections,copy,hashlib,json,re,shutil,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261027C.smc2')
DEST=SOURCE.with_name(SOURCE.name.replace('20261027C','20261027D'))
STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'
EXPECTED='ec193e7ab0c4934ac44136c89d2206c762bc19a0c4581051a7cd999ce03f8508'
NAME='ST7_A_Dis2_M'
PAT=re.compile(r'(?<![A-Za-z0-9_])ST7_A_Dis2_M\[\s*(\d+)\s*\]')
TARGET_SUFFIX='1c62506a-fffa-4120-bf30-bcfd518c76f9.xml'
NEW_COMMENTS={16:'排出フォルダ送り行',17:'SF/NG2左右 移動開始',18:'SF/NG2上下 目標位置転送',
              22:'SF/NG2上下 移動開始',23:'SF/NG2上下 原点位置転送',24:'SF/NG2上下 原点移動開始',
              25:'SF/NG2左右 原点位置転送',26:'SF/NG2左右 原点移動開始'}
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def fields(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
def renamed(s,keep16=False,last_coil=False):
    def change(m):
        ix=int(m[1])
        if last_coil and ix==24:return NAME+'[26]'
        if ix>=17 or (ix==16 and not keep16):return NAME+f'[{ix+1}]'
        return m[0]
    return PAT.sub(change,s)

def build():
    assert not DEST.exists(),'既存D版を上書きしません'
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert source_hash==EXPECTED,'確認後にC版が更新されています'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
    texts={}
    for n,raw in original.items():
        try:t=raw.decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' not in t:texts[n]=t
    target=next(n for n in texts if n.endswith(TARGET_SUFFIX))
    changes={};references=[];counts={};old_target=None;new_target=None
    for n,t in texts.items():
        if not t.lstrip().startswith('{'):continue
        try:old=[json.loads(l) for l in t.splitlines() if l.strip()]
        except Exception:continue
        if not old or not all('CLs' in r for r in old):continue
        counts[n]=len(old);new=copy.deepcopy(old)
        if n==target:assert len(old)==24
        for i,row in enumerate(new):
            for node in walk(row):
                for key in ('Var','TXT'):
                    if not isinstance(node.get(key),str):continue
                    before=node[key]
                    node[key]=renamed(before,keep16=(n==target and i==10),
                                      last_coil=(n==target and i==17 and node.get('__type')=='ST' and key=='Var'))
                    if node[key]!=before:references.append({'entry':n,'row':i,'type':node.get('__type'),'field':key,'before':before,'after':node[key]})
            assert row.get('CMT')==old[i].get('CMT'),'行コメント本文は保持'
        if n==target:old_target,new_target=old,new
        if new!=old:
            lines=t.splitlines(keepends=True)
            assert len(lines)==len(old)
            for i,(a,b) in enumerate(zip(old,new)):
                if a!=b:
                    end=lines[i][len(lines[i].rstrip('\r\n')):]
                    lines[i]=json.dumps(b,ensure_ascii=False,separators=(',',':'))+end
            changes[n]=''.join(lines)
    assert old_target and new_target
    def coils(rows):
        return collections.Counter(int(PAT.fullmatch(node['Var'])[1]) for row in rows for node in walk(row)
                                   if node.get('__type')=='ST' and PAT.fullmatch(node.get('Var','')))
    before_coils=coils(old_target);after_coils=coils(new_target)
    assert before_coils[16]==before_coils[24]==2
    assert after_coils=={i:1 for i in range(1,27)},after_coils
    assert old_target[10]==new_target[10],'上側16番のシリンダ行は全データ保持'
    assert old_target[18:]==new_target[18:],'後続のSF処理は全データ保持'
    assert any(node.get('Var')==NAME+'[17]' and node.get('Not') for node in walk(new_target[9]))
    assert any(node.get('Var')==NAME+'[17]' and node.get('__type')=='ST' for node in walk(new_target[11]))
    assert any(node.get('Var')==NAME+'[25]' and node.get('__type')=='LD' for node in walk(new_target[17]))
    assert any(node.get('Var')==NAME+'[26]' and node.get('__type')=='ST' for node in walk(new_target[17]))
    assert all(PAT.fullmatch(node['Var']) and int(PAT.fullmatch(node['Var'])[1])<=26 for row in new_target for node in walk(row)
               if isinstance(node.get('Var'),str) and node['Var'].startswith(NAME+'['))
    # 元の要素説明は添字を一回だけ移動。分離した16/17・25/26の説明も新しい段階へ対応させる。
    globals_name=next(n for n,t in texts.items() if t.startswith('[SLWD') and '+GN=VAR_GLOBAL' in t)
    global_line=next(l for l in texts[globals_name].splitlines() if l.startswith('++D=') and fields(l)['N']==NAME)
    gp=fields(global_line);root=ET.fromstring(gp.get('EC','<ECs/>'))
    element_comments={}
    for e in root:
        m=re.fullmatch(r'\[(\d+)\]',e.get('EK',''));assert m
        old_ix=int(m[1]);new_ix=old_ix+1 if old_ix>=16 else old_ix
        assert new_ix not in element_comments
        element_comments[new_ix]=e.get('C','')
    for ix,c in NEW_COMMENTS.items():
        assert ix not in element_comments or element_comments[ix]==c,('既存説明を上書きする衝突',ix)
        element_comments[ix]=c
    ec=ET.Element('ECs')
    for ix,c in sorted(element_comments.items()):ET.SubElement(ec,'EC',EK=f'[{ix}]',C=c)
    ec_text=ET.tostring(ec,encoding='unicode')
    declaration_entries=[]
    for n,t in texts.items():
        if not t.startswith('[SLWD'):continue
        lines=[];hit=False
        for line in t.splitlines(keepends=True):
            if line.startswith('++D=') and fields(line.rstrip('\r\n'))['N']==NAME:
                ending=line[len(line.rstrip('\r\n')):];p=fields(line.rstrip('\r\n'))
                assert re.fullmatch(r'ARRAY\[0\.\.99\] OF BOOL',p['D'],re.I)
                parts=line.rstrip('\r\n')[2:].split('\t');at=next((i for i,v in enumerate(parts) if v.startswith('EC=')),None)
                if at is None:parts.append('EC='+ec_text)
                else:parts[at]='EC='+ec_text
                line='++'+'\t'.join(parts)+ending
                after=fields(line.rstrip('\r\n'));a,b=dict(p),dict(after);a.pop('EC',None);b.pop('EC',None);assert a==b
                hit=True
            lines.append(line)
        if hit:
            changed=''.join(lines);declaration_entries.append(n)
            if changed!=t:changes[n]=changed
    assert len(declaration_entries)==3
    # 元データへ指定変換をもう一度適用してから、保存側と比較する。
    # これにより、接点の否定・命令・配線・タイマー・他変数・行コメントへの差分を禁止する。
    for n in counts:
        source_rows=[json.loads(l) for l in texts[n].splitlines() if l.strip()]
        after_rows=[json.loads(l) for l in changes.get(n,texts[n]).splitlines() if l.strip()]
        expected=copy.deepcopy(source_rows)
        for i,row in enumerate(expected):
            for node in walk(row):
                for key in ('Var','TXT'):
                    if isinstance(node.get(key),str):node[key]=renamed(node[key],keep16=(n==target and i==10),last_coil=(n==target and i==17 and node.get('__type')=='ST' and key=='Var'))
        assert expected==after_rows
    for n,t in texts.items():
        if n not in counts and not t.startswith('[SLWD'):
            assert not PAT.search(t),('ラダー以外の添字参照は要確認',n)
    assert not any(n.endswith(('.dat','.oem')) for n in changes)
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=comment
        for info in infos:
            raw=original[info.filename]
            if info.filename in changes:raw=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changes[info.filename].encode('utf-8')
            z.writestr(info,raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        assert all(z.read(n)==raw for n,raw in original.items() if n not in changes)
        for n in changes:assert z.read(n).decode('utf-8-sig')==changes[n]
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':source_hash,
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'entries':len(original),'changed_entries':list(changes),
            'reference_changes':references,'reference_change_count':len(references),'coils_before':dict(sorted(before_coils.items())),
            'coils_after':dict(sorted(after_coils.items())),'element_comments_after':element_comments,'declaration_entries':declaration_entries,
            'upper_16_rung_fully_preserved':True,'forward_iai_start_contact_updated_to_17':True,
            'only_approved_indices_and_element_comments_changed':True,'ladder_counts':counts,'native_validation':None,
            'native_comments_validation':None,'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['reference_changes','ladder_counts','element_comments_after','coils_before','coils_after']},ensure_ascii=False,indent=2))

def publish():
    r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert r['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
    assert r['native_comments_validation']
    assert r['independent_audit']['unique_coils_1_to_26'] and r['independent_audit']['reference_mapping_checked_by_row']
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
    with STAGED.open('rb') as a,DEST.open('xb') as b:shutil.copyfileobj(a,b)
    assert hashlib.sha256(DEST.read_bytes()).hexdigest()==r['output_sha256']
    r['published']=True;REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)
if __name__=='__main__':publish() if '--publish' in sys.argv else build()
