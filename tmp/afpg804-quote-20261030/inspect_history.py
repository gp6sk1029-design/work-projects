"""会社Thunderbirdの送信済みを読取り専用で調べ、福西宛の直近メールを照合する。"""
from pathlib import Path
import json,mmap,re,sys
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
ROOT=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp')
def normal(data):
 return b''.join(l for l in data.replace(b'\r\r\n',b'\r\n').splitlines(keepends=True) if not l.startswith(b'>From '))
hits=[]
with (ROOT/'Sent').open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as mm:
 sep=list(re.finditer(rb'(?m)^From [^\n]*\n',mm))
 for i,m in enumerate(sep):
  start=m.end();end=sep[i+1].start() if i+1<len(sep) else len(mm)
  head=normal(mm[start:min(end,start+18000)])
  if b'denzai.jp' not in head.lower():continue
  h=BytesParser(policy=policy.default).parsebytes(head,headersonly=True)
  if 'denzai.jp' not in str(h['To']).lower():continue
  if int(str(h['X-Mozilla-Status'] or '0'),16)&8:continue
  try:ts=parsedate_to_datetime(str(h['Date'])).timestamp()
  except Exception:continue
  hits.append({'start':start,'end':end,'timestamp':ts,**{k:str(h[k] or '') for k in ('From','To','Cc','Subject','Date','Message-ID')}})
 hits.sort(key=lambda x:x['timestamp'],reverse=True)
 latest=hits[:3]
 for row in latest:
  msg=BytesParser(policy=policy.default).parsebytes(normal(mm[row['start']:row['end']]))
  body=msg.get_body(preferencelist=('plain','html'));row['body_preview']=body.get_content()[:1600] if body else ''
assert latest,'福西宛の履歴がありません'
(BASE/'history.json').write_text(json.dumps(latest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(latest,ensure_ascii=False,indent=2))
