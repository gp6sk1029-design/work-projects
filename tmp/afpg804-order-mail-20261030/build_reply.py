"""元見積回答の返信情報を保持した添付付き未送信EMLを用意する。"""
from pathlib import Path
from email.message import EmailMessage
from email.parser import BytesParser
from email import policy
from email.utils import format_datetime,make_msgid,getaddresses
from datetime import datetime
import hashlib,json,sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).resolve().parent
source=json.loads((b/'reply_source.json').read_text(encoding='utf-8'))
assert 'AFPG804' in source['Subject'] and getaddresses([source['From']])[0][1]=='kimura.yuko@denzai.jp'
pdf=Path(r'\\nas-ime5\生産技術部\scan\注文書【AF-K261030-1】.pdf')
data=pdf.read_bytes();digest=hashlib.sha256(data).hexdigest()
assert digest=='2716db2a512c27769ae5d843d3abcd913082cc00e6a0af3ba833beff7980a9e4'
body=(b/'注文メール本文.txt').read_text(encoding='utf-8').strip()
quote='\n'.join('> '+line for line in source['body'].splitlines())
msg=EmailMessage(policy=policy.SMTP)
msg['From']='幸田 祥平 <sy-kouda@ime-group.co.jp>'
msg['To']='木村様【福西電機】 <kimura.yuko@denzai.jp>'
msg['Cc']=source['Cc']
msg['Subject']='Re: 見積依頼【FPΣ用バックアップ電池 AFPG804／10個】'
msg['Date']=format_datetime(datetime.now().astimezone())
msg['Message-ID']=make_msgid(domain='ime-group.co.jp')
msg['In-Reply-To']=source['Message-ID']
msg['References']=(source['References']+' '+source['Message-ID']).strip()
msg['X-Unsent']='1'
msg.set_content(body+'\n\n'+source['Date']+' 木村様：\n'+quote+'\n')
msg.add_attachment(data,maintype='application',subtype='pdf',filename=pdf.name)
out=b/'注文書_AF-K261030-1_未送信.eml'
out.write_bytes(msg.as_bytes())
check=BytesParser(policy=policy.default).parsebytes(out.read_bytes())
assert check['In-Reply-To']==source['Message-ID']
assert {a for _,a in getaddresses([str(check['Cc'])])}=={a for _,a in getaddresses([source['Cc']])}
parts=list(check.iter_attachments());assert len(parts)==1
assert parts[0].get_filename()==pdf.name and hashlib.sha256(parts[0].get_payload(decode=True)).hexdigest()==digest
report={'eml':str(out),'to':str(check['To']),'cc':str(check['Cc']),'subject':str(check['Subject']),'reply_to':source['Message-ID'],'attachment':str(pdf),'attachment_sha256':digest,'attachment_bytes':len(data),'eml_verified':True,'thunderbird_drafts_saved':False,'sent':False,'ui_error':'failed to activate captured window'}
(b/'draft_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
