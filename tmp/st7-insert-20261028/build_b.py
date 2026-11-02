"""新規５段を保持し、旧ST7段階の繰下げ・二重コイル分離・MOVE軸整合を行う。"""
from pathlib import Path
import collections,copy,hashlib,json,re,shutil,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261029A.smc2')
DEST=SOURCE.with_name(SOURCE.name.replace('20261029A','20261029B'))
STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'
EXPECTED='4ab4ec4efb14152785855b53104fe3c42896f64ef9c62fa5653d665ed522a9e1'
NAME='ST7_A_Dis2_M';TARGET_SUFFIX='1c62506a-fffa-4120-bf30-bcfd518c76f9.xml'
PAT=re.compile(r'(?<![A-Za-z0-9_])ST7_A_Dis2_M\[\s*(\d+)\s*\]')
NEW_COMMENT={12:'コンベア下降 位置転送',13:'コンベア下降 移動開始',14:'排出チャック開 行',
             15:'セイフティ上昇 位置転送',16:'セイフティ上昇 移動開始',27:'ストックフォルダ条件保持',
             32:'排出フォルダ送り戻',33:'排出フォルダ戻完了'}
def fields(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def old_index(ix):return ix+6 if ix>=22 else ix+5 if ix>=12 else ix
def map_ref(s,n,i,node,row,target):
    def replace(m):
        ix=int(m[1])
        # 新規9～13行目と、それを開始させる前段は番号を保持する。
        if n==target and i<14:return m[0]
        # 旧工程入口の最初の接点だけは、新規工程の最終16番を参照する。
        if n==target and i==14 and node is row['CLs'][0]:
            assert ix==16 and node.get('__type')=='LD'
            return m[0]
        # 先にある22番の独立保持段は27番、後のIAI開始22番は28番へ分離。
        if n==target and i==18 and ix==22:return NAME+'[27]'
        return NAME+f'[{old_index(ix)}]'
    return PAT.sub(replace,s)

def transform(rows,n,target,log=None):
    after=copy.deepcopy(rows)
    for i,row in enumerate(after):
        for node in walk(row):
            for key in ('Var','TXT'):
                if not isinstance(node.get(key),str):continue
                before=node[key];node[key]=map_ref(before,n,i,node,row,target)
                if log is not None and node[key]!=before:log.append({'entry':n,'row':i,'type':node.get('__type'),'field':key,'before':before,'after':node[key]})
        if n==target:
            for node in walk(row):
                if node.get('Name')!='MOVE':continue
                ins=[p for p in node.get('In',[]) if p.get('Arg')=='In']
                outs=[p for p in node.get('Out',[]) if p.get('Arg')=='Out']
                if not ins or not outs:continue
                match=re.fullmatch(r'HMI_RCON1_([35])_OUT_TargetPos\[\d+\]',ins[0].get('Var',''))
                if not match:continue
                new='RCON1_'+match[1]+'_OUT_TargetPos_mm'
                if outs[0].get('Var')!=new:
                    before=outs[0]['Var'];outs[0]['Var']=new
                    if log is not None:log.append({'entry':n,'row':i,'type':'MOVE','field':'Out','before':before,'after':new})
    return after

def build():
    assert not DEST.exists(),'既存B版は上書きしません'
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert source_hash==EXPECTED,'確認後にA版が更新されています'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
    texts={};ladders={}
    for n,raw in original.items():
        try:t=raw.decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' in t:continue
        texts[n]=t
        if t.lstrip().startswith('{'):
            try:rs=[json.loads(l) for l in t.splitlines() if l.strip()]
            except Exception:continue
            if rs and all('CLs' in r for r in rs):ladders[n]=rs
    target=next(n for n in ladders if n.endswith(TARGET_SUFFIX))
    assert len(ladders[target])==31
    changes={};refs=[];counts={n:len(rs) for n,rs in ladders.items()}
    for n,old in ladders.items():
        after=transform(old,n,target,refs)
        if old!=after:
            ls=texts[n].splitlines(keepends=True);assert len(ls)==len(old)
            for i,(a,b) in enumerate(zip(old,after)):
                assert a.get('CMT')==b.get('CMT'),'行コメント本文は保持'
                if a!=b:
                    end=ls[i][len(ls[i].rstrip('\r\n')):]
                    ls[i]=json.dumps(b,ensure_ascii=False,separators=(',',':'))+end
            changes[n]=''.join(ls)
    new=transform(ladders[target],target,target)
    def coils(rows):return collections.Counter(int(PAT.fullmatch(node['Var'])[1]) for row in rows for node in walk(row) if node.get('__type')=='ST' and PAT.fullmatch(node.get('Var','')))
    before_coils=coils(ladders[target]);after_coils=coils(new)
    assert all(before_coils[i]==2 for i in [12,13,14,15,16,22])
    assert after_coils=={i:1 for i in range(1,34)},after_coils
    fixes=[r for r in refs if r['type']=='MOVE']
    assert collections.Counter(r['row'] for r in fixes)=={3:1,5:1,9:1,12:1,17:7,20:1,22:1}
    assert sum(n in changes for n in ladders)==1,'対象外のラダーは変更しない'
    assert new[:3]==ladders[target][:3]
    assert new[25:]==ladders[target][25:],'後続の別配列SF処理は保持'
    assert new[14]['CLs'][0]==ladders[target][14]['CLs'][0]
    for i in [10,11,13]:assert new[i]==ladders[target][i]
    # 既存のコメントを旧工程の新番号へ移動し、新規12～16には実際の工程説明を割り当てる。
    global_name=next(n for n,t in texts.items() if t.startswith('[SLWD') and '+GN=VAR_GLOBAL' in t)
    gp=fields(next(l for l in texts[global_name].splitlines() if l.startswith('++D=') and fields(l)['N']==NAME))
    old_ec={int(e.get('EK')[1:-1]):e.get('C','') for e in ET.fromstring(gp['EC'])}
    comments={old_index(ix):c for ix,c in old_ec.items()}
    assert comments[18]==old_ec[13] and comments[19]==old_ec[14] and comments[20]==old_ec[15]
    # 32番は以前の左右移動開始ではなく、現行ではフォルダ戻指令に変更されている。
    comments.update(NEW_COMMENT)
    ec=ET.Element('ECs')
    for ix,c in sorted(comments.items()):ET.SubElement(ec,'EC',EK=f'[{ix}]',C=c)
    ec_text=ET.tostring(ec,encoding='unicode')
    declarations=[]
    for n,t in texts.items():
        if not t.startswith('[SLWD'):continue
        ls=[];hit=False
        for line in t.splitlines(keepends=True):
            if line.startswith('++D=') and fields(line.rstrip('\r\n'))['N']==NAME:
                end=line[len(line.rstrip('\r\n')):];p=fields(line.rstrip('\r\n'))
                assert re.fullmatch(r'ARRAY\[0\.\.99\] OF BOOL',p['D'],re.I)
                parts=line.rstrip('\r\n')[2:].split('\t');idx=next((i for i,v in enumerate(parts) if v.startswith('EC=')),None)
                if idx is None:parts.append('EC='+ec_text)
                else:parts[idx]='EC='+ec_text
                line='++'+'\t'.join(parts)+end
                q=fields(line.rstrip('\r\n'));a,b=dict(p),dict(q);a.pop('EC',None);b.pop('EC',None);assert a==b
                hit=True
            ls.append(line)
        if hit:
            declarations.append(n)
            if ''.join(ls)!=t:changes[n]=''.join(ls)
    assert len(declarations)==3
    assert len(comments)==25 and set(comments)==set(range(9,34))
    # 名称・I/O・型定義やバイナリの固定添字参照は自動で変更しない。
    for n,t in texts.items():
        if n not in ladders and not t.startswith('[SLWD'):assert not PAT.search(t),('別形式の添字参照',n)
    for n,raw in original.items():
        if n not in texts:
            assert not any(f'{NAME}[{i}]'.encode(enc) in raw for enc in ['utf-8','utf-16-le'] for i in range(12,100)),('バイナリ内の添字参照',n)
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
        for n,old in ladders.items():
            saved=[json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
            assert saved==transform(old,n,target)
    blanks=[{'row':i,'node_ix':node.get('Ix')} for i,row in enumerate(new) for node in walk(row) if node.get('__type')=='LD' and node.get('Var')=='']
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':source_hash,
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'entries':len(original),'changed_entries':list(changes),
            'reference_changes':refs,'index_reference_change_count':len(refs)-len(fixes),'move_fixes':fixes,'move_fix_count':len(fixes),
            'coils_before':dict(sorted(before_coils.items())),'coils_after':dict(sorted(after_coils.items())),
            'element_comments_after':comments,'declaration_entries':declarations,'blank_contacts_preserved':blanks,
            'isolated_step_27_preserved_no_downstream_connection_added':True,'later_sf_processing_unchanged':True,
            'ladder_counts':counts,'native_validation':None,'native_comments_validation':None,'independent_audit':None,
            'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['reference_changes','move_fixes','coils_before','coils_after','element_comments_after','ladder_counts','blank_contacts_preserved']},ensure_ascii=False,indent=2))
    print('未入力接点（元から・変更なし）',len(blanks))

def publish():
    r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert r['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
    assert r['native_comments_validation'] and r['independent_audit']
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
    with STAGED.open('rb') as a,DEST.open('xb') as b:shutil.copyfileobj(a,b)
    assert hashlib.sha256(DEST.read_bytes()).hexdigest()==r['output_sha256']
    r['published']=True;REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)
if __name__=='__main__':publish() if '--publish' in sys.argv else build()
