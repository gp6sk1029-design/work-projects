"""欠番27を詰め、旧28～33の参照と要素コメントを１つ繰り上げる。"""
from pathlib import Path
import collections,copy,hashlib,json,re,shutil,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261029B.smc2')
DEST=SOURCE.with_name(SOURCE.name.replace('20261029B','20261029C'))
STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'
EXPECTED='2697e2c811f24254b4a6d7fa65f6577e58a5b32988050f3d79dce2b3b264a154'
NAME='ST7_A_Dis2_M';PAT=re.compile(r'(?<![A-Za-z0-9_])ST7_A_Dis2_M\[\s*(\d+)\s*\]')
def rename(s):return PAT.sub(lambda m:NAME+f'[{int(m[1])-1}]' if int(m[1])>=28 else m[0],s)
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def fields(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
def build():
    assert not DEST.exists(),'既存C版を上書きしません'
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED,'調査後にB版が更新されています'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
    texts={}
    for n,raw in original.items():
        try:t=raw.decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' not in t:texts[n]=t
    changes={};counts={};refs=[];comments_by_entry={};before_coils=collections.Counter();after_coils=collections.Counter();blanks=[]
    for n,t in texts.items():
        if not t.lstrip().startswith('{'):continue
        try:rows=[json.loads(l) for l in t.splitlines() if l.strip()]
        except Exception:continue
        if not rows or not all('CLs' in r for r in rows):continue
        counts[n]=len(rows);after=copy.deepcopy(rows)
        for i,row in enumerate(after):
            for node in walk(row):
                for key in ['Var','TXT']:
                    if not isinstance(node.get(key),str):continue
                    before=node[key]
                    assert not any(int(m[1])==27 for m in PAT.finditer(before)),('欠番ではない参照',n,i)
                    node[key]=rename(before)
                    if node[key]!=before:refs.append({'entry':n,'row':i,'field':key,'type':node.get('__type'),'before':before,'after':node[key]})
                if node.get('__type')=='ST' and PAT.fullmatch(node.get('Var','')):after_coils[int(PAT.fullmatch(node['Var'])[1])]+=1
                if n.endswith('1c62506a-fffa-4120-bf30-bcfd518c76f9.xml') and node.get('__type')=='LD' and node.get('Var')=='':blanks.append(i)
            assert row.get('CMT')==rows[i].get('CMT')
        for node in walk(rows):
            if node.get('__type')=='ST' and PAT.fullmatch(node.get('Var','')):before_coils[int(PAT.fullmatch(node['Var'])[1])]+=1
        if rows!=after:
            ls=t.splitlines(keepends=True);assert len(ls)==len(rows)
            for i,(a,b) in enumerate(zip(rows,after)):
                if a!=b:
                    end=ls[i][len(ls[i].rstrip('\r\n')):]
                    ls[i]=json.dumps(b,ensure_ascii=False,separators=(',',':'))+end
            changes[n]=''.join(ls)
    assert before_coils=={i:1 for i in list(range(1,27))+list(range(28,34))}
    assert after_coils=={i:1 for i in range(1,33)}
    assert len(refs)==19,len(refs)
    for n,t in texts.items():
        if not t.startswith('[SLWD'):continue
        lines=[];hit=False
        for line in t.splitlines(keepends=True):
            if line.startswith('++D=') and fields(line.rstrip('\r\n'))['N']==NAME:
                end=line[len(line.rstrip('\r\n')):];p=fields(line.rstrip('\r\n'));old_ec=ET.fromstring(p['EC']);new_ec=ET.Element('ECs')
                old_comments={e.get('EK'):e.get('C') for e in old_ec}
                for e in old_ec:
                    ix=int(e.get('EK')[1:-1])
                    if ix==27:continue
                    copy_e=copy.deepcopy(e)
                    if ix>=28:copy_e.set('EK',f'[{ix-1}]')
                    new_ec.append(copy_e)
                new_comments={e.get('EK'):e.get('C') for e in new_ec}
                assert all(new_comments.get(f'[{i}]')==old_comments.get(f'[{i+1}]') for i in range(27,33))
                assert all(new_comments.get(f'[{i}]')==old_comments.get(f'[{i}]') for i in range(0,27))
                assert len(new_ec)==len(old_ec)-1 and len(new_comments)==len(new_ec)
                ec_text=ET.tostring(new_ec,encoding='unicode')
                parts=line.rstrip('\r\n')[2:].split('\t')
                idx=next(i for i,v in enumerate(parts) if v.startswith('EC='));parts[idx]='EC='+ec_text
                line='++'+'\t'.join(parts)+end
                q=fields(line.rstrip('\r\n'));p.pop('EC');q.pop('EC');assert p==q
                comments_by_entry[n]=new_comments;hit=True
            lines.append(line)
        if hit:changes[n]=''.join(lines)
    assert len(comments_by_entry)==3
    assert len(changes)==4 and not any(n.endswith(('.dat','.oem')) for n in changes)
    for n,t in texts.items():
        if n not in counts and not t.startswith('[SLWD'):assert not PAT.search(t),('別形式の参照は要確認',n)
    for n,raw in original.items():
        if n not in texts:
            assert not any(f'{NAME}[{i}]'.encode(enc) in raw for enc in ['utf-8','utf-16-le'] for i in range(27,100)),('バイナリ参照は要確認',n)
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=comment
        for info in infos:
            raw=original[info.filename]
            if info.filename in changes:raw=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changes[info.filename].encode('utf-8')
            z.writestr(info,raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        assert all(z.read(n)==raw for n,raw in original.items() if n not in changes)
        for n in counts:
            old=[json.loads(l) for l in texts[n].splitlines() if l.strip()]
            saved=[json.loads(l) for l in z.read(n).decode('utf-8-sig').splitlines() if l.strip()]
            expected=copy.deepcopy(old)
            for node in walk(expected):
                for key in ['Var','TXT']:
                    if isinstance(node.get(key),str):node[key]=rename(node[key])
            assert expected==saved,'添字以外のラダー差分'
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':EXPECTED,
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'entries':len(original),'changed_entries':list(changes),
            'reference_changes':refs,'reference_change_count':len(refs),'coils_after':dict(sorted(after_coils.items())),
            'comments_by_entry':comments_by_entry,'ladder_counts':counts,'blank_contacts_preserved':blanks,
            'native_validation':None,'native_comments_validation':None,'independent_audit':None,
            'only_indices_and_element_comments_changed':True,'no_rungs_added_or_deleted':True,
            'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['reference_changes','coils_after','comments_by_entry','ladder_counts','blank_contacts_preserved']},ensure_ascii=False,indent=2))
    print('未入力接点（元から・保持）',len(blanks))
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
