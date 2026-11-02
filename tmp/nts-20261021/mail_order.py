"""アドレス帳と既存メールを読み取り専用で照合し、未送信メールを準備する。"""
from pathlib import Path
import sqlite3, json, sys, mmap, re, hashlib
from email import policy
from email.parser import BytesParser
from email.message import EmailMessage
from email.utils import format_datetime,make_msgid
from datetime import datetime
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding='utf-8')
D=Path(__file__).parent
PROFILE=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release')
ROOT=PROFILE/'Mail'/'mail.ime-group.co.jp'

def normal(data):
    return b''.join(l for l in data.replace(b'\r\r\n',b'\r\n').splitlines(keepends=True) if not l.startswith(b'>From '))

if sys.argv[1]=='contacts':
    found=[]
    for db in sorted(PROFILE.glob('abook*.sqlite')):
        conn=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
        tables=[r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type=?',('table',))]
        if 'properties' not in tables: continue
        rows=conn.execute('SELECT card,name,value FROM properties').fetchall()
        cards={}
        for card,name,value in rows: cards.setdefault(card,{})[name]=value
        for card,v in cards.items():
            if any(n in ' '.join(str(x) for x in v.values()) for n in ('三木','藤田','安井','エヌ・ティー','NTS')):
                found.append({'db':db.name,'card':card,**{k:v[k] for k in ('DisplayName','FirstName','LastName','PrimaryEmail','SecondEmail','Company','Department','JobTitle') if k in v}})
        conn.close()
    (D/'contacts.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(found,ensure_ascii=False,indent=2))
elif sys.argv[1]=='mailfind':
    contacts=json.loads((D/'contacts.json').read_text(encoding='utf-8'))
    needles=[r.get('PrimaryEmail','').lower().encode() for r in contacts if r.get('PrimaryEmail','') in ('m.miki@fa-nts.com','nts-miki@leto.eonet.ne.jp')]
    assert needles
    found=[]
    for path in (ROOT/'Inbox',ROOT/'Sent'):
        with path.open('rb') as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
            starts=[m.end() for m in re.finditer(rb'(?m)^From [^\n]*\n',mm)]
            for i,start in enumerate(starts):
                end=starts[i+1] if i+1<len(starts) else len(mm)
                head=mm[start:min(end,start+20000)]
                # ヘッダー中の空行以降は本文。対象メールだけ全文を解析する。
                h=BytesParser(policy=policy.default).parsebytes(normal(head),headersonly=True)
                addresses=' '.join(str(h[k] or '') for k in ('From','To','Cc')).lower().encode()
                if not any(n in addresses for n in needles): continue
                row={'path':str(path),'start':start,'end':end,**{k:str(h[k] or '') for k in ('From','To','Cc','Subject','Date','Message-ID')}}
                found.append(row)
            print(path.name,'該当',len(found),flush=True)
    for row in found[-10:]:
        with Path(row['path']).open('rb') as f:
            f.seek(row['start']);msg=BytesParser(policy=policy.default).parsebytes(normal(f.read(row['end']-row['start'])))
        body=msg.get_body(preferencelist=('plain','html'))
        row['body']=(body.get_content() if body else '')[:6000]
        row['attachments']=[p.get_filename() for p in msg.iter_attachments()]
    (D/'nts_mail_history.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(found[-6:],ensure_ascii=False,indent=2))
elif sys.argv[1]=='build':
    pdf=Path(r'\\nas-ime5\生産技術部\scan\注文書【AU-K261021-1】.pdf')
    body='''有限会社エヌ・ティー・エス
三木様

いつも大変お世話になっております。
一宮電機の幸田です。

添付の注文書のとおり、下記部品の手配をお願いいたします。

注文番号：AU-K261021-1
品名：電磁弁用コイル（CKD）
型式：4F9-P5132-M0E-DC24V
数量：5個
用途：アマチュアコア修繕 部品

ご確認のうえ、納期をご連絡いただけますと幸いです。
よろしくお願いいたします。

株式会社 一宮電機
生産技術部　幸田 祥平
TEL：0791-59-8205
E-mail：sy-kouda@ime-group.co.jp
'''
    m=EmailMessage(policy=policy.SMTP)
    m['From']='幸田 祥平 <sy-kouda@ime-group.co.jp>'
    m['To']='三木 学 様 <m.miki@fa-nts.com>'
    m['Cc']='藤田様（生産技術部） <ch-fujita@ime-group.co.jp>, 安井工場長 <yu-yasui@ime-group.co.jp>'
    m['Subject']='注文書送付【AU-K261021-1／アマチュアコア修繕部品】'
    m['Date']=format_datetime(datetime.now(ZoneInfo('Asia/Tokyo')))
    m['Message-ID']=make_msgid(domain='ime-group.co.jp')
    m['X-Unsent']='1'
    m.set_content(body)
    attachment=pdf.read_bytes()
    assert hashlib.sha256(attachment).hexdigest()=='f2da1cf7fe871d6f664f70ca241a1d28de75a3d1c3d25dcba51f8aacf9755ebb'
    m.add_attachment(attachment,maintype='application',subtype='pdf',filename=pdf.name)
    out=Path(r'C:\Users\SEIGI-N13\Desktop\注文メール_NTS_AU-K261021-1_未送信.eml')
    assert not out.exists(),'上書きしない'
    out.write_bytes(m.as_bytes())
    check=BytesParser(policy=policy.default).parsebytes(out.read_bytes())
    assert list(check.iter_attachments())[0].get_payload(decode=True)==attachment
    print(json.dumps({'file':str(out),'to':str(check['To']),'cc':str(check['Cc']),'subject':str(check['Subject']),'attachment':pdf.name},ensure_ascii=False,indent=2))
