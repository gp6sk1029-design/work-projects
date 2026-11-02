from pathlib import Path
import email.policy
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
import hashlib
import json
import shutil
import sys
from openpyxl import load_workbook

sys.stdout.reconfigure(encoding='utf-8')
work=Path(__file__).parent
name='【見積依頼書】_巻線機オーバーホール新規制御部品_SLM-8000_20261019.xlsx'
created=Path(r'C:\Users\SEIGI-N13\work-projects\outputs\quote-20261019')/name
target=Path(r'\\nas-ime5\生産技術部\2.見積 決裁願\見積\1_見積依頼書\2026')/name
draftdir=Path(r'C:\Users\SEIGI-N13\Desktop\巻線機オーバーホール_見積依頼_20261019')
draftpath=draftdir/'見積依頼メール_テクノ高尾様_未送信.eml'

# 作成済みファイルを読み取り検証し、原紙に無関係な値変更がないか確認する。
before=load_workbook(work/'template.xlsx')
after=load_workbook(created)
assert before.sheetnames==after.sheetnames==['原紙']
expected={'B6':'依頼件名：巻線機オーバーホール新規制御部品','C18':'SLM-8000','D18':'制御機器(配線等を含む)','F18':2,'G13':'幸田'}
assert set(map(str,before.active.merged_cells.ranges))==set(map(str,after.active.merged_cells.ranges))
for row in before.active:
    for cell in row:
        assert after.active[cell.coordinate].value==expected.get(cell.coordinate,cell.value),(cell.coordinate,cell.value,after.active[cell.coordinate].value)
for addr,value in expected.items():
    assert after.active[addr].value==value
assert after.active['B8'].value=='希望納期：'
if target.exists() or draftpath.exists():
    raise FileExistsError('同名成果物が既に存在するため、上書きせず停止します。')

body='''株式会社テクノ
高尾 様

いつも大変お世話になります。
一宮電機の幸田です。

巻線機オーバーホールに伴う新規制御部品について、
見積依頼書を送付させていただきます。

依頼件名：巻線機オーバーホール新規制御部品
型式：SLM-8000
品名：制御機器(配線等を含む)
数量：2

お見積りと併せて、発注後の納期もご連絡いただけますと幸いです。
なお、今回は見積依頼のみであり、発注ではございません。

お手数をおかけしますが、よろしくお願いいたします。

--
/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
株式会社　一宮電機
  生産技術部
     幸田　祥平 （Shohei Koda）
〒679-5165
兵庫県たつの市新宮町光都1丁目1179-17
TEL ： 0791-59-8205
FAX ： 0791-59-8213
E-mail ： sy-kouda@ime-group.co.jp
/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/
'''
msg=EmailMessage(policy=email.policy.SMTP)
msg['From']=formataddr(('幸田 祥平','sy-kouda@ime-group.co.jp'))
msg['To']=formataddr(('株式会社テクノ 高尾様','mail@open-mc.com'))
msg['Cc']=', '.join([formataddr(('中村 智 次長','sa-nakamura@ime-group.co.jp')),formataddr(('八木 工場長','a-yagi@ime-group.co.jp'))])
msg['Subject']='見積依頼書の送付【巻線機オーバーホール新規制御部品／SLM-8000】'
msg['X-Unsent']='1'
msg['X-Identity-Key']='id1'
msg['Message-ID']=make_msgid(domain='ime-group.co.jp')
msg.set_content(body)
payload=created.read_bytes()
msg.add_attachment(payload,maintype='application',subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename=name)
draftdir.mkdir(parents=True,exist_ok=True)
shutil.copy2(created,target)
shutil.copy2(created,draftdir/name)
with draftpath.open('xb') as output:
    output.write(msg.as_bytes())
from email.parser import BytesParser
check=BytesParser(policy=email.policy.default).parsebytes(draftpath.read_bytes())
assert check['X-Unsent']=='1'
attachments=list(check.iter_attachments())
assert len(attachments)==1 and attachments[0].get_payload(decode=True)==payload
assert check['To'].addresses[0].addr_spec=='mail@open-mc.com'
assert {a.addr_spec for a in check['Cc'].addresses}=={'sa-nakamura@ime-group.co.jp','a-yagi@ime-group.co.jp'}
assert target.read_bytes()==payload
print(json.dumps({'xlsx':str(target),'draft':str(draftpath),'desktop':str(draftdir),'attachment_sha256':hashlib.sha256(payload).hexdigest(),'changed_cells':expected,'sent':False},ensure_ascii=False,indent=2))
