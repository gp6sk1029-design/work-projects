"""AFPG804見積回答だけを会社メールから読取り専用で確認する。"""
from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import json,mmap,re,sys
sys.stdout.reconfigure(encoding='utf-8')
B=Path(__file__).resolve().parent
ROOT=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp')
def normal(data):
 return b''.join(l for l in data.replace(b'\r\r\n',b'\r\n').splitlines(keepends=True) if not l.startswith(b'>From '))
hits=[]
for box in ['Inbox.sbd/1_社内.sbd/他部署.sbd/2_社外','Sent']:
 p=ROOT/box
 with p.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
  sep=list(re.finditer(rb'(?m)^From [^\n]*\n',mm))
  for i,m in enumerate(sep):
   end=sep[i+1].start() if i+1<len(sep) else len(mm)
   h=BytesParser(policy=policy.default).parsebytes(normal(mm[m.end():min(end,m.end()+18000)]),headersonly=True)
   if 'afpg804' not in str(h.get('Subject','')).replace(' ','').replace('\t','').lower():continue
   if box=='Sent' and int(str(h.get('X-Mozilla-Status','0')),16)&8:continue
   msg=BytesParser(policy=policy.default).parsebytes(normal(mm[m.end():end]))
   body=msg.get_body(preferencelist=('plain','html'))
   hits.append({'box':box,**{k:str(msg.get(k,'')) for k in ['From','To','Cc','Subject','Date','Message-ID','References','In-Reply-To','X-Mozilla-Status']},'body':body.get_content()[:5500] if body else '', 'attachments':[x.get_filename() for x in msg.iter_attachments()]})
hits.sort(key=lambda x:parsedate_to_datetime(x['Date']).timestamp(),reverse=True)
(B/'mail_history.json').write_text(json.dumps(hits,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(hits[:5],ensure_ascii=False,indent=2))
