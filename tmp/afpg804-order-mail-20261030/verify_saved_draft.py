"""Thunderbird下書きを読取り専用で照合する。"""
from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
import hashlib,json,re,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).resolve().parent
expected=json.loads((b/'draft_result.json').read_text(encoding='utf-8'))
p=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp\Drafts')
with p.open('rb') as f:
 f.seek(max(0,p.stat().st_size-10_000_000));data=f.read()
hits=[]
for raw in re.split(rb'(?m)^From [^\n]*\n',data)[1:]:
 raw=raw.replace(b'\r\r\n',b'\r\n')
 raw=b''.join(x for x in raw.splitlines(keepends=True) if not re.match(rb'^>+From ',x))
 m=BytesParser(policy=policy.default).parsebytes(raw)
 if int(str(m.get('X-Mozilla-Status','0')),16)&8:continue
 if 'AFPG804' not in str(m.get('Subject','')):continue
 body=m.get_body(preferencelist=('plain','html'));text=body.get_content() if body else ''
 if 'AF-K261030-1' not in text:continue
 parts=list(m.iter_attachments())
 row={k:str(m.get(k,'')) for k in ['From','To','Cc','Subject','Date','Message-ID','In-Reply-To','References']}
 row['attachments']=[{'name':x.get_filename(),'sha256':hashlib.sha256(x.get_payload(decode=True)).hexdigest(),'bytes':len(x.get_payload(decode=True))} for x in parts]
 row['raw_reply_headers']={k:v for k,v in m.raw_items() if k.lower() in ['in-reply-to','references']}
 row['recipient_ok']=[a for _,a in getaddresses([row['To']])]==['kimura.yuko@denzai.jp']
 row['cc_ok']={a for _,a in getaddresses([row['Cc']])}=={a for _,a in getaddresses([expected['cc']])}
 row['attachment_ok']=len(parts)==1 and row['attachments'][0]['sha256']==expected['attachment_sha256']
 row['thread_ok']=row['In-Reply-To']==expected['reply_to'] and expected['reply_to'] in row['References']
 row['body_ok']=all(x in text for x in ['AFPG804','10個','1,050円','10,500円','生産技術部 幸田宛'])
 hits.append(row)
print(json.dumps({'matching_active_drafts':len(hits),'drafts':hits},ensure_ascii=False,indent=2))
if len(hits)==1 and all(hits[0][x] for x in ['recipient_ok','cc_ok','attachment_ok','thread_ok','body_ok']):
 (b/'saved_draft_verification.json').write_text(json.dumps(hits[0],ensure_ascii=False,indent=2),encoding='utf-8')
