"""宛先を読み取り専用で確認する。"""
from pathlib import Path
import sqlite3,json,sys,mmap,re
from email import policy
from email.parser import BytesParser
sys.stdout.reconfigure(encoding='utf-8')
P=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release')
D=Path(__file__).parent
if sys.argv[1]=='contacts':
    found=[]
    for db in P.glob('abook*.sqlite'):
        with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as c:
            if not c.execute("SELECT name FROM sqlite_master WHERE name='properties'").fetchone():continue
            cards={}
            for card,k,v in c.execute('SELECT card,name,value FROM properties'):cards.setdefault(card,{})[k]=v
            for v in cards.values():
                if any(n in ' '.join(str(x) for x in v.values()) for n in ('八木','中村','藤田')):
                    found.append({'db':db.name,**{k:v[k] for k in ('DisplayName','PrimaryEmail','Company','Department','JobTitle') if k in v}})
    (D/'contacts.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(found,ensure_ascii=False,indent=2))
elif sys.argv[1]=='history':
    found=[]
    for path in (P/'Mail'/'mail.ime-group.co.jp'/'Inbox',P/'Mail'/'mail.ime-group.co.jp'/'Sent'):
        with path.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
            starts=[m.start() for m in re.finditer(rb'(?m)^From [^\n]*\n',mm)]
            for i,s in enumerate(starts):
                e=starts[i+1] if i+1<len(starts) else len(mm)
                start=mm.find(b'\n',s)+1
                raw=mm[start:min(e,start+18000)].replace(b'\r\r\n',b'\r\n')
                h=BytesParser(policy=policy.default).parsebytes(raw,headersonly=True)
                a=' '.join(str(h[k] or '') for k in ('From','To','Cc')).lower()
                if not any(n in a for n in ('yagi.keisuke','nakamura@imanaga','imanaga','@omron.com')):continue
                row={'path':str(path),'start':start,'end':e,**{k:str(h[k] or '') for k in ('From','To','Cc','Subject','Date','Message-ID')}}
                if '@omron.com' in a or 'imanaga' in a:found.append(row)
    (D/'history.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(found[-35:],ensure_ascii=False,indent=2))
elif sys.argv[1]=='verify':
    path=P/'Mail'/'mail.ime-group.co.jp'/'Drafts'
    with path.open('rb') as f:
        f.seek(max(0,path.stat().st_size-5000000));raw=f.read().replace(b'\r\r\n',b'\r\n')
    starts=[m.start() for m in re.finditer(rb'(?m)^From [^\n]*\n',raw)]
    found=[]
    for i,s in enumerate(starts):
        e=starts[i+1] if i+1<len(starts) else len(raw)
        m=BytesParser(policy=policy.default).parsebytes(raw[raw.find(b'\n',s)+1:e])
        if str(m['Subject'] or '')!='見積依頼【750W・キー付きサーボモータ／パルス列用アンプ 各4台】':continue
        body=m.get_body(preferencelist=('plain','html'))
        text=body.get_content() if body else ''
        assert 'katsuaki.yagi@omron.com' in str(m['To'])
        assert all(a in str(m['Cc']) for a in ('sa-nakamura@ime-group.co.jp','m.nakamura@imanaga.co.jp','ch-fujita@ime-group.co.jp'))
        assert all(t in text for t in ('R88M-K75030H-S2','R88D-KT08H','4台','納期'))
        found.append({k:str(m[k] or '') for k in ('Subject','To','Cc','Date')})
        print(text)
    assert found,'実際の下書き保存が未確認'
    print(json.dumps(found[-1],ensure_ascii=False,indent=2))
