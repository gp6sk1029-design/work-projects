"""前回送信メールの宛先を照合し、添付付き未送信メールを準備する。送信やmbox書込みは行わない。"""
from pathlib import Path
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import format_datetime, make_msgid, getaddresses
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,sys
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
history=json.loads((BASE/'current_mail_history.json').read_text(encoding='utf-8'))
prev=next(x for x in history if x['folder']=='Sent' and 'AU-K261021-1' in x['Subject'])
assert [a for _,a in getaddresses([prev['To']])]==['m.miki@fa-nts.com']
assert [a for _,a in getaddresses([prev['Cc']])]==['ch-fujita@ime-group.co.jp','yu-yasui@ime-group.co.jp']
pdf=Path(r'\\nas-ime5\生産技術部\scan\注文書【AU-K261028-1】.pdf')
attachment=pdf.read_bytes()
assert hashlib.sha256(attachment).hexdigest()=='5e8fba633c9e4f57b9398109222ad592b960bb4be3ab97c28e831a0675671e16'
body='''有限会社エヌ・ティー・エス
三木様

いつも大変お世話になっております。
一宮電機の幸田です。

添付の注文書のとおり、下記部品の手配をお願いいたします。

注文番号：AU-K261028-1
品名：電磁弁（CKD）
型式：4GB210R-08-E00-1
数量：3個
請求先：光都工場
納入先：生産技術部 武田宛

ご確認のうえ、納期をご連絡いただけますと幸いです。
よろしくお願いいたします。
'''
m=EmailMessage(policy=policy.SMTP)
m['From']=prev['From'];m['To']=prev['To'];m['Cc']=prev['Cc']
m['Subject']='注文書送付【AU-K261028-1／CKD 電磁弁】'
m['Date']=format_datetime(datetime.now(ZoneInfo('Asia/Tokyo')))
m['Message-ID']=make_msgid(domain='ime-group.co.jp');m['X-Unsent']='1'
m.set_content(body)
m.add_attachment(attachment,maintype='application',subtype='pdf',filename=pdf.name)
out=BASE/'注文メール_NTS_AU-K261028-1_未送信.eml'
assert not out.exists()
out.write_bytes(m.as_bytes())
check=BytesParser(policy=policy.default).parsebytes(out.read_bytes())
assert list(check.iter_attachments())[0].get_payload(decode=True)==attachment
assert str(check['X-Unsent'])=='1'
print(json.dumps({'file':str(out),'subject':str(check['Subject']),'to':str(check['To']),'cc':str(check['Cc']),'attachment':pdf.name,'size':len(attachment)},ensure_ascii=False))
