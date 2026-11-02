"""スキャンPDFと送信履歴を読み取り専用で確認する。"""
from pathlib import Path
import hashlib, json, mmap, re, sys
from email import policy
from email.parser import BytesParser
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
ROOT=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp')
def normal(b):
    return b''.join(l for l in b.replace(b'\r\r\n',b'\r\n').splitlines(keepends=True) if not l.startswith(b'>From '))
if sys.argv[1]=='history':
    hits=[]
    for path in [ROOT/'Sent',ROOT/'Drafts']:
        if not path.exists() or not path.stat().st_size: continue
        with path.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
            sep=list(re.finditer(rb'(?m)^From [^\n]*\n',mm))
            for i,m in enumerate(sep):
                start=m.end(); end=sep[i+1].start() if i+1<len(sep) else len(mm)
                h=BytesParser(policy=policy.default).parsebytes(normal(mm[start:min(end,start+18000)]),headersonly=True)
                if 'm.miki@fa-nts.com' not in str(h['To']).lower(): continue
                row={'folder':path.name,'start':start,'end':end,**{k:str(h[k] or '') for k in ('From','To','Cc','Subject','Date','Message-ID')}}
                if '261021' in row['Subject'] or '261028' in row['Subject']:
                    msg=BytesParser(policy=policy.default).parsebytes(normal(mm[start:end]))
                    body=msg.get_body(preferencelist=('plain','html'))
                    row['body']=body.get_content() if body else ''
                    row['attachments']=[{'filename':p.get_filename(),'size':len(p.get_payload(decode=True) or b''),'sha256':hashlib.sha256(p.get_payload(decode=True) or b'').hexdigest()} for p in msg.iter_attachments()]
                hits.append(row)
    (BASE/'current_mail_history.json').write_text(json.dumps(hits,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([x for x in hits if '261021' in x['Subject'] or '261028' in x['Subject']],ensure_ascii=False,indent=2))
    print('NTS履歴',len(hits))
elif sys.argv[1]=='pdf':
    import fitz
    pdf=Path(r'\\nas-ime5\生産技術部\scan\20261028142952308.pdf')
    doc=fitz.open(pdf)
    print('PDF',pdf.name,'ページ',len(doc),'SHA256',hashlib.sha256(pdf.read_bytes()).hexdigest())
    for i,page in enumerate(doc):
        print('TEXT',i+1,page.get_text()[:1600])
        page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(BASE/f'scan-{i+1}.png')
