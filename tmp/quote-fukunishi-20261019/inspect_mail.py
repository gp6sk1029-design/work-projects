import email
import email.policy
from email.header import decode_header, make_header
import json
import sys
from pathlib import Path
from html import unescape
import re
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp')
WORK=Path(__file__).parent
def dec(value):
    try:return str(make_header(decode_header(value or '')))
    except Exception:return str(value or '')
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
rows=[]
for start,end,headers in records(ROOT/'Sent'):
    h=email.message_from_bytes(headers,policy=email.policy.compat32)
    to=dec(h.get('To'))
    if any(t in to.lower() for t in ['福西','fujimoto.keita@denzai.jp','kimura.yuko@denzai.jp']):
        rows.append({'Date':dec(h.get('Date')),'To':to,'Cc':dec(h.get('Cc')),'Subject':dec(h.get('Subject')),'start':start,'end':end})
selected=[r for r in rows if any(t in r['Subject'] for t in ['サーボ','モータ','巻線','パナソニック','Panasonic','見積'])]
for row in selected[-15:]:
    with (ROOT/'Sent').open('rb') as f:
        f.seek(row['start']);msg=email.message_from_bytes(f.read(row['end']-row['start']),policy=email.policy.default)
    parts=[];attachments=[]
    for part in msg.walk():
        filename=part.get_filename()
        if filename:
            attachments.append(filename)
            if filename.lower().endswith('.pdf'):
                out=WORK/'past_attachments'/str(row['start'])/Path(filename).name
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_bytes(part.get_payload(decode=True))
        elif part.get_content_type() in ['text/plain','text/html']:
            try:
                text=part.get_content()
                if part.get_content_type()=='text/html':text=unescape(re.sub('<[^>]+>',' ',text))
                parts.append(text)
            except Exception:pass
    row.update(body='\n'.join(parts)[:8000],attachments=attachments)
result={'all_recent':rows[-15:],'related':selected[-15:]}
(WORK/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
