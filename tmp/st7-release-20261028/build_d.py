"""新規19行目の28番を保全し、20行目以降の旧28～32を29～33へ移す。"""
from pathlib import Path
import collections,copy,hashlib,json,re,shutil,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261029C.smc2')
DEST=SOURCE.with_name(SOURCE.name.replace('20261029C','20261029D'));STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'
EXPECTED='fe9ef4aa07d2d3fb228a7a883a49338b8d5e1a82255e78eff38919a09da6f072'
NAME='ST7_A_Dis2_M';PAT=re.compile(r'(?<![A-Za-z0-9_])ST7_A_Dis2_M\[\s*(\d+)\s*\]')
TARGET_SUFFIX='1c62506a-fffa-4120-bf30-bcfd518c76f9.xml'
def rename(s):return PAT.sub(lambda m:NAME+f'[{int(m[1])+1}]' if int(m[1])>=28 else m[0],s)
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def fields(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
def build():
    assert not DEST.exists(),'既存D版を上書きしません'
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED,'確認後にC版が更新されました'
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
    target=next(n for n in ladders if n.endswith(TARGET_SUFFIX));assert len(ladders[target])==31
    changes={};refs=[];comments_by_entry={}
    for n,rows in ladders.items():
        after=copy.deepcopy(rows)
        for i,row in enumerate(after):
            if n==target and i<20:continue
            for node in walk(row):
                for key in ['Var','TXT']:
                    if not isinstance(node.get(key),str):continue
                    old=node[key];node[key]=rename(old)
                    if node[key]!=old:refs.append({'entry':n,'row':i,'field':key,'type':node.get('__type'),'before':old,'after':node[key]})
        if rows!=after:
            lines=texts[n].splitlines(keepends=True)
            for i,(a,b) in enumerate(zip(rows,after)):
                assert a.get('CMT')==b.get('CMT')
                if a!=b:
                    ending=lines[i][len(lines[i].rstrip('\r\n')):]
                    lines[i]=json.dumps(b,ensure_ascii=False,separators=(',',':'))+ending
            changes[n]=''.join(lines)
    assert len(refs)==14 and all(x['entry']==target for x in refs)
    for n,t in texts.items():
        if not t.startswith('[SLWD'):continue
        lines=[];hit=False
        for line in t.splitlines(keepends=True):
            if line.startswith('++D=') and fields(line.rstrip('\r\n'))['N']==NAME:
                ending=line[len(line.rstrip('\r\n')):];p=fields(line.rstrip('\r\n'));old_ec=ET.fromstring(p['EC'])
                old_comments={int(e.get('EK')[1:-1]):e.get('C','') for e in old_ec}
                new_comments={(i+1 if i>=28 else i):c for i,c in old_comments.items()}
                assert 28 not in new_comments
                new_comments[28]='排出チャック戻／ワーク解放'
                root=ET.Element('ECs')
                for i,c in sorted(new_comments.items()):ET.SubElement(root,'EC',EK=f'[{i}]',C=c)
                ec_text=ET.tostring(root,encoding='unicode')
                parts=line.rstrip('\r\n')[2:].split('\t');at=next(i for i,v in enumerate(parts) if v.startswith('EC='));parts[at]='EC='+ec_text
                line='++'+'\t'.join(parts)+ending
                q=fields(line.rstrip('\r\n'));p.pop('EC');q.pop('EC');assert p==q
                comments_by_entry[n]={f'[{i}]':c for i,c in new_comments.items()};hit=True
            lines.append(line)
        if hit:changes[n]=''.join(lines)
    assert len(comments_by_entry)==3 and len(changes)==4
    for n,t in texts.items():
        if n not in ladders and not t.startswith('[SLWD'):assert not PAT.search(t),('別形式の添字参照',n)
    for n,raw in original.items():
        if n not in texts:assert not any(f'{NAME}[{i}]'.encode(enc) in raw for enc in ['utf-8','utf-16-le'] for i in range(28,100)),n
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
        saved=[json.loads(l) for l in z.read(target).decode('utf-8-sig').splitlines() if l.strip()]
        assert saved[:20]==ladders[target][:20]
        c=collections.Counter(int(PAT.fullmatch(node['Var'])[1]) for row in saved for node in walk(row) if node.get('__type')=='ST' and PAT.fullmatch(node.get('Var','')))
        assert c=={i:1 for i in range(1,34)}
        blanks=[i for i,row in enumerate(saved) for node in walk(row) if node.get('__type')=='LD' and node.get('Var')=='']
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':EXPECTED,
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'entries':len(original),'changed_entries':list(changes),
            'reference_changes':refs,'reference_change_count':len(refs),'comments_by_entry':comments_by_entry,
            'ladder_counts':{n:len(rows) for n,rows in ladders.items()},'blank_contacts_preserved':blanks,
            'new_release_rung_19_fully_preserved':True,'previous_step_18_stop_contact_28_preserved':True,
            'next_row_20_start_condition_27_and_move_done_preserved':True,'no_release_completion_link_added':True,
            'native_validation':None,'native_comments_validation':None,'independent_audit':None,
            'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['reference_changes','comments_by_entry','ladder_counts']},ensure_ascii=False,indent=2))
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
