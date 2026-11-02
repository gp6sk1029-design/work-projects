from pathlib import Path
from email.parser import BytesParser
from email.message import EmailMessage
from email.utils import make_msgid
import email.policy
import sys
sys.stdout.reconfigure(encoding='utf-8')
folder=Path(r'C:\Users\SEIGI-N13\Desktop\巻線機オーバーホール_福西電機見積依頼_20261019')
name='見積依頼メール_福西電機様_未送信.eml'
oldbytes=(folder/'変更前_詳細メール'/name).read_bytes()
assert (folder/name).read_bytes()==oldbytes,'作業中にメールが変更されました'
old=BytesParser(policy=email.policy.default).parsebytes(oldbytes)
body=(folder/'メール本文_確認用.txt').read_text(encoding='utf-8-sig')
new=EmailMessage(policy=email.policy.SMTP)
for key in ['From','To','Cc','Subject','X-Unsent','X-Identity-Key']:
    new[key]=str(old[key])
new['Message-ID']=make_msgid(domain='ime-group.co.jp')
new.set_content(body)
attachments=list(old.iter_attachments())
for part in attachments:
    new.add_attachment(part.get_payload(decode=True),maintype=part.get_content_maintype(),subtype=part.get_content_subtype(),filename=part.get_filename())
data=new.as_bytes()
check=BytesParser(policy=email.policy.default).parsebytes(data)
assert check['X-Unsent']=='1'
for key in ['To','Cc']:
    assert {a.addr_spec for a in check[key].addresses}=={a.addr_spec for a in old[key].addresses}
updated=list(check.iter_attachments())
assert len(updated)==len(attachments)==2
assert all(a.get_payload(decode=True)==b.get_payload(decode=True) for a,b in zip(updated,attachments))
assert 'MSMF022L1A1' in check.get_body(preferencelist=('plain',)).get_content()
with (folder/name).open('wb') as stream:stream.write(data)
print('メール本文を簡潔化。宛先・CC・添付2件不変。未送信。')
