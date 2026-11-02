import email
import email.policy
import json
import re
import sys
from html import unescape
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).parent
evidence=json.loads((root/'mail_evidence.json').read_text(encoding='utf-8'))
mailroot=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp')
for row in evidence['templates']+evidence['techno'][-3:]:
    with (mailroot/row['mailbox']).open('rb') as stream:
        stream.seek(row['start'])
        msg=email.message_from_bytes(stream.read(row['end']-row['start']),policy=email.policy.default)
    parts=[]
    for part in msg.walk():
        if part.get_content_type() in ['text/plain','text/html'] and part.get_content_disposition() != 'attachment':
            text=part.get_content()
            if part.get_content_type()=='text/html':
                text=re.sub(r'<(?:br\s*/?|/p|/div)>','\n',text,flags=re.I)
                text=unescape(re.sub(r'<[^>]+>','',text))
            parts.append(text)
    print(json.dumps({'subject':row['Subject'],'to':row['To'],'body':'\n'.join(parts)[:9000]},ensure_ascii=False))
