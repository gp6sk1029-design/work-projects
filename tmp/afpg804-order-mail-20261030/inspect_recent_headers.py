"""対象取引先フォルダ末尾の見積回答ヘッダーを読取り確認する。"""
from pathlib import Path
from email import policy
from email.parser import BytesParser
import mmap,re,sys,json
sys.stdout.reconfigure(encoding='utf-8')
p=Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp\Inbox.sbd\1_社内.sbd\他部署.sbd\2_社外')
with p.open('rb') as f:
 f.seek(max(0,p.stat().st_size-25_000_000));data=f.read()
chunks=re.split(rb'(?m)^From [^\n]*\n',data)[1:]
rows=[]
for raw in chunks:
 if b'kimura.yuko@denzai.jp' not in raw[:18000].lower():continue
 raw=raw.replace(b'\r\r\n',b'\r\n').lstrip(b'\r\n')
 raw=b''.join(line for line in raw.splitlines(keepends=True) if not re.match(rb'^>+From ',line))
 msg=BytesParser(policy=policy.default).parsebytes(raw)
 rows.append({k:str(msg.get(k,'')) for k in ['From','To','Cc','Subject','Date','Message-ID','References','In-Reply-To']})
 if 'AFPG804' in str(msg.get('Subject','')):
  selected=rows[-1].copy()
  body=msg.get_body(preferencelist=('plain','html'))
  selected['body']=body.get_content() if body else ''
  (Path(__file__).resolve().parent/'reply_source.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows[-5:],ensure_ascii=False,indent=2))
print('対象メール件数',len(rows),'末尾区切り件数',len(chunks))
