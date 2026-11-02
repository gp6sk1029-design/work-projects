"""確認した最新送信先を使って未送信EMLを準備する。メールボックスには書かない。"""
from pathlib import Path
from email.message import EmailMessage
from email.parser import BytesParser
from email import policy
from email.utils import make_msgid,format_datetime
from datetime import datetime
from zoneinfo import ZoneInfo
import json,sys
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
history=json.loads((BASE/'history.json').read_text(encoding='utf-8'))[0]
msg=EmailMessage(policy=policy.SMTP)
for key in ('From','To','Cc'):msg[key]=history[key]
msg['Subject']='見積依頼【FPΣ用バックアップ電池 AFPG804／10個】'
msg['Message-ID']=make_msgid(domain='ime-group.co.jp')
msg['Date']=format_datetime(datetime.now(ZoneInfo('Asia/Tokyo')))
msg['X-Unsent']='1'
signature=history['body_preview'].split('/-/-/-/',1)
assert len(signature)==2
footer='/-/-/-/'+signature[1].strip()
body='''福西電機株式会社
木村様

いつもお世話になっております。
一宮電機の幸田です。

下記製品のお見積りと納期をご回答いただけますでしょうか。

メーカー：パナソニック
品名：FPΣ用バックアップ電池
型式：AFPG804
数量：10個
使用機器：FPΣ AFPG2543

お手数をおかけいたしますが、よろしくお願いいたします。

'''+footer+'\n'
msg.set_content(body,charset='utf-8')
path=BASE/'福西電機_AFPG804_10個_見積依頼_未送信.eml'
with path.open('xb') as f:f.write(msg.as_bytes())
saved=BytesParser(policy=policy.default).parsebytes(path.read_bytes())
assert [a.addr_spec for a in saved['To'].addresses]==['kimura.yuko@denzai.jp']
assert [a.addr_spec for a in saved['Cc'].addresses]==['sa-nakamura@ime-group.co.jp','a-yagi@ime-group.co.jp','fujimoto.keita@denzai.jp','ch-fujita@ime-group.co.jp']
assert all(s in saved.get_content() for s in ('AFPG804','10個','AFPG2543','納期'))
assert not list(saved.iter_attachments())
result={'file':str(path),'subject':str(saved['Subject']),'to':str(saved['To']),'cc':str(saved['Cc']),'message_id':str(saved['Message-ID']),'body':saved.get_content(),'thunderbird_draft_saved':False,'sent':False}
(BASE/'draft.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='body'},ensure_ascii=False,indent=2))
