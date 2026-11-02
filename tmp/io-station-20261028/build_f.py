"""所属確定済みのI/OコメントだけへSTを追記し、原本Eを保持する。"""
from pathlib import Path
import collections,hashlib,html,json,re,shutil,sys,zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from station_rules import update
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
D=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
SRC=Path(D['source']);DEST=SRC.with_name(SRC.name.replace('20261029E','20261029F'));STAGED=BASE/DEST.name
RP=BASE/'verification.json'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fields(l):return dict(x.split('=',1) for x in l[2:].split('\t') if '=' in x)
def build():
    assert digest(SRC)==D['sha256'],'調査後に原本Eが変わっています'
    assert not DEST.exists() and not STAGED.exists(),'既存Fは上書きしません'
    with zipfile.ZipFile(SRC) as z:
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();zc=z.comment
    changes={};edits=[];decl_changes=[]
    def change(value,entry,kind):
        new=update(value)
        if new!=value:edits.append({'entry':entry,'kind':kind,'old':value,'new':new})
        return new
    def attributes(xml,entry,keys):
        pat=re.compile(r'(?P<head>\b(?:'+ '|'.join(keys)+r')=")(?P<value>[^"]*)(?P<tail>")')
        def sub(m):
            old=html.unescape(m['value']);new=change(old,entry,'XML属性コメント')
            if old==new:return m[0]
            return m['head']+escape(new,{'"':'&quot;','\r':'&#13;','\n':'&#10;','\t':'&#9;'})+m['tail']
        return pat.sub(sub,xml)
    for n,t in D['texts'].items():
        after=t
        if t.startswith('[SLWD'):
            lines=[]
            for line in t.splitlines(keepends=True):
                if line.startswith('++D='):
                    ending=line[len(line.rstrip('\r\n')):];parts=line.rstrip('\r\n')[2:].split('\t')
                    oldp=fields(line.rstrip('\r\n'))
                    for i,part in enumerate(parts):
                        if part.startswith('Com='):parts[i]='Com='+change(part[4:],n,'変数コメント')
                        elif part.startswith('EC='):parts[i]='EC='+attributes(part[3:],n,['C'])
                    line='++'+'\t'.join(parts)+ending
                    newp=fields(line.rstrip('\r\n'))
                    assert {k:v for k,v in oldp.items() if k not in ('Com','EC')}=={k:v for k,v in newp.items() if k not in ('Com','EC')}
                    if oldp!=newp:decl_changes.append({'entry':n,'name':oldp['N'],'old_comment':oldp.get('Com'),'new_comment':newp.get('Com'),'type':oldp['D'],'group':oldp['G']})
                lines.append(line)
            after=''.join(lines)
        elif n in D['ladder_counts']:
            lines=[]
            for line in t.splitlines(keepends=True):
                if line.strip():
                    row=json.loads(line);old=row.get('CMT','');new=change(old,n,'行コメント')
                    if new!=old:
                        row['CMT']=new;ending=line[len(line.rstrip('\r\n')):]
                        line=json.dumps(row,ensure_ascii=False,separators=(',',':'))+ending
                lines.append(line)
            after=''.join(lines)
        elif t.lstrip().startswith('<'):
            ET.fromstring(t)
            after=attributes(t,n,['Comment','Com','CMT'])
            # 表示用XMLのコメント要素と、I/O名札に限り同じ表記へ揃える。
            pat=re.compile(r'(?P<open><(?P<tag>(?:[\w]+:)?(?:Comment|Com|CMT|Text))\b[^>]*>)(?P<body>[^<]*)(?P<close></(?P=tag)>)')
            def element(m):
                old=html.unescape(m['body']);new=change(old,n,'XML要素コメント')
                return m[0] if old==new else m['open']+escape(new)+m['close']
            after=pat.sub(element,after)
            ET.fromstring(after)
        if after!=t:changes[n]=after
    assert len(edits)>0 and not any(n.endswith(('.dat','.oem')) for n in changes)
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=zc
        for info in infos:
            raw=original[info.filename]
            if info.filename in changes:raw=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changes[info.filename].encode('utf-8')
            z.writestr(info,raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        assert all(z.read(n)==raw for n,raw in original.items() if n not in changes)
    r={'source':str(SRC),'destination':str(DEST),'staged':str(STAGED),'source_sha256':D['sha256'],'output_sha256':digest(STAGED),
       'entries':len(original),'changed_entries':list(changes),'comment_edits':edits,'comment_counts':dict(collections.Counter(e['kind'] for e in edits)),
       'declaration_changes':decl_changes,'ladder_counts':D['ladder_counts'],'native_validation':None,'native_comments':None,'independent_audit':None,
       'app_build_verified':False,'machine_transfer_performed':False}
    RP.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items() if k not in ('comment_edits','declaration_changes','ladder_counts')},ensure_ascii=False,indent=2))
def publish():
    r=json.loads(RP.read_text(encoding='utf-8-sig'))
    assert r['independent_audit'] and r['native_comments'] and r['native_validation']
    assert all('PARSE_FAIL=0 MODEL_FAIL=0' in x for x in r['native_validation'].values())
    assert digest(SRC)==r['source_sha256'] and digest(STAGED)==r['output_sha256']
    with STAGED.open('rb') as a,DEST.open('xb') as b:shutil.copyfileobj(a,b)
    assert digest(DEST)==r['output_sha256']
    r['published']=True;RP.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)
if __name__=='__main__':publish() if '--publish' in sys.argv else build()
