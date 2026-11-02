from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from datetime import datetime
from zoneinfo import ZoneInfo
import json, sys, hashlib

sys.stdout.reconfigure(encoding='utf-8')
D=Path(__file__).parent
ROOT=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp')

def normalize(data):
    data=data.replace(b'\r\r\n',b'\r\n')
    # ローカル保管メールの転送用envelope行はRFCメールヘッダーではない。
    return b''.join(line for line in data.splitlines(keepends=True) if not line.startswith(b'>From '))

def records(path):
    with path.open('rb') as f:
        start=None; headers=[]; inhead=False
        while True:
            offset=f.tell();line=f.readline()
            if not line:
                if start is not None:yield start,offset,b''.join(headers)
                break
            if line.startswith(b'From '):
                if start is not None:yield start,offset,b''.join(headers)
                start=f.tell();headers=[];inhead=True
            elif inhead:
                headers.append(line)
                if not line.strip():inhead=False

if sys.argv[1]=='find':
    found=[]
    for path in [ROOT/'Inbox']:
        if not path.is_file():continue
        for start,end,headers in records(path):
            h=BytesParser(policy=policy.default).parsebytes(normalize(headers))
            if 'open-mc.com' not in str(h['From']).lower():continue
            found.append({'path':str(path),'start':start,'end':end,**{k:str(h[k] or '') for k in ['From','To','Cc','Subject','Date','Message-ID','References']}})
    selected=found[-8:]
    for row in selected:
        with Path(row['path']).open('rb') as f:
            f.seek(row['start']);m=BytesParser(policy=policy.default).parsebytes(normalize(f.read(row['end']-row['start'])))
        b=m.get_body(preferencelist=('plain','html'))
        row['body']=b.get_content() if b else ''
        row['attachments']=[p.get_filename() for p in m.iter_attachments()]
    (D/'source_mail.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(selected,ensure_ascii=False,indent=2))
elif sys.argv[1]=='build':
    rows=json.loads((D/'source_mail.json').read_text(encoding='utf-8'))
    row=next(r for r in reversed(rows) if '20 Oct 2026' in r['Date'] and 'hyamanaka@open-mc.com' in r['From'])
    pdf=Path(r'\\nas-ime5\生産技術部\scan\注文書【2717-2610A-T1】.pdf')
    body='''株式会社テクノ
山中様

いつもお世話になっております。
株式会社一宮電機 生産技術部の幸田です。

お見積りをご回答いただき、ありがとうございました。
添付の注文書のとおり、下記を発注いたします。

注文番号：2717-2610A-T1
品名：ワンボードモーションコントローラ一式
型式：SLM-8000
数量：2台
注文金額：712,000円（税別・送料込み）
貴社お見積No.：TB02-3819

注文書をご確認のうえ、納期をご連絡いただけますと幸いです。
よろしくお願いいたします。

株式会社一宮電機
生産技術部　幸田 祥平
sy-kouda@ime-group.co.jp
'''
    m=EmailMessage(policy=policy.SMTP)
    m['From']='幸田 祥平 <sy-kouda@ime-group.co.jp>'
    m['To']=row['From']+', 株式会社テクノ <mail@open-mc.com>'
    m['Cc']=row['Cc']
    m['Subject']=row['Subject'] if row['Subject'].lower().startswith('re:') else 'Re: '+row['Subject']
    m['In-Reply-To']=row['Message-ID']
    m['References']=(row['References']+' '+row['Message-ID']).strip()
    m['Date']=format_datetime(datetime.now(ZoneInfo('Asia/Tokyo')))
    m['Message-ID']=make_msgid(domain='ime-group.co.jp')
    m['X-Unsent']='1'
    m.set_content(body+'\n\n----- 元の見積回答 -----\n'+row['body'])
    payload=pdf.read_bytes()
    m.add_attachment(payload,maintype='application',subtype='pdf',filename=pdf.name)
    out=Path(r'C:\Users\SEIGI-N13\Desktop')/'注文メール_テクノ_2717-2610A-T1_未送信.eml'
    assert not out.exists(), '既存ファイルに上書きしません'
    out.write_bytes(m.as_bytes())
    check=BytesParser(policy=policy.default).parsebytes(out.read_bytes())
    attachments=list(check.iter_attachments())
    assert len(attachments)==1 and attachments[0].get_payload(decode=True)==payload
    assert check['In-Reply-To']==row['Message-ID'] and check['X-Unsent']=='1'
    print(json.dumps({'file':str(out),'To':str(check['To']),'Cc':str(check['Cc']),'Subject':str(check['Subject']),'attachment':pdf.name,'pdf_sha256':hashlib.sha256(payload).hexdigest()},ensure_ascii=False))
