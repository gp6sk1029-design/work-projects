import email
import email.policy
import json
from pathlib import Path
from email.header import decode_header, make_header

ROOT = Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp')

def decoded(value):
    try:
        return str(make_header(decode_header(value or '')))
    except Exception:
        return str(value or '')

def records(path):
    # メール本文・添付を展開せず、まずヘッダーだけを読む。
    with path.open('rb') as stream:
        start = None
        headers = []
        reading_headers = False
        while True:
            offset = stream.tell()
            line = stream.readline()
            if not line:
                if start is not None:
                    yield start, offset, b''.join(headers)
                break
            if line.startswith(b'From '):
                if start is not None:
                    yield start, offset, b''.join(headers)
                start = stream.tell()
                headers = []
                reading_headers = True
            elif reading_headers:
                headers.append(line)
                if not line.strip():
                    reading_headers = False

def body_of(path, start, end):
    with path.open('rb') as stream:
        stream.seek(start)
        msg = email.message_from_bytes(stream.read(end-start), policy=email.policy.default)
    parts=[]
    for part in msg.walk():
        if part.get_content_type() == 'text/plain' and part.get_content_disposition() != 'attachment':
            try:
                parts.append(part.get_content())
            except Exception:
                pass
    return '\n'.join(parts)[:18000]

result={'templates':[], 'techno':[], 'cc_candidates':[]}
for filename in ['Templates','Sent']:
    path=ROOT/filename
    if not path.exists():
        continue
    for start,end,headers in records(path):
        h=email.message_from_bytes(headers,policy=email.policy.compat32)
        row={key:decoded(h.get(key)) for key in ['Date','From','To','Cc','Subject','Message-ID']}
        row.update(start=start,end=end,mailbox=filename)
        if filename=='Templates':
            row['body']=body_of(path,start,end)
            result['templates'].append(row)
        elif any(term in (row['To']+' '+row['Subject']).lower() for term in ['テクノ','techno','slm-8000','slm8000']):
            result['techno'].append(row)
        if filename=='Sent' and any(term in (row['To']+' '+row['Cc']) for term in ['中村','八木']):
            result['cc_candidates'].append(row)
result['techno']=result['techno'][-16:]
for row in result['techno'][-5:]:
    row['body']=body_of(ROOT/row['mailbox'],row['start'],row['end'])
result['cc_candidates']=result['cc_candidates'][-12:]
out=Path(__file__).parent/'mail_evidence.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
