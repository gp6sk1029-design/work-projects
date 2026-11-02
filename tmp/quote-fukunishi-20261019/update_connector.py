from pathlib import Path
import email.policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import make_msgid
import json
import hashlib
import shutil
import sys
from openpyxl import load_workbook

sys.stdout.reconfigure(encoding='utf-8')
work=Path(__file__).parent
folder=Path(r'C:\Users\SEIGI-N13\Desktop\巻線機オーバーホール_福西電機見積依頼_20261019')
backup=folder/'変更前_リード線仕様'
name='【見積依頼書】_巻線機オーバーホール_サーボモータ・アンプ_福西電機_20261019.xlsx'
created=Path(r'C:\Users\SEIGI-N13\work-projects\outputs\quote-fukunishi-20261019')/name
nas=Path(r'\\nas-ime5\生産技術部\2.見積 決裁願\見積\1_見積依頼書\2026')/name
eml_name='見積依頼メール_福西電機様_未送信.eml'
old=BytesParser(policy=email.policy.default).parsebytes((backup/eml_name).read_bytes())
body=(folder/'メール本文_確認用.txt').read_text(encoding='utf-8-sig')
assert 'MSMF022L1A1' in body and 'MSMF042L1B1' in body
assert 'MSMF022L1A2' not in body and 'MSMF042L1B2' not in body
assert '3種類すべてコネクタタイプ' in body
before=load_workbook(backup/name)
after=load_workbook(created)
expected={'C20':'MSMF022L1A1','C22':'MSMF042L1B1'}
assert before.sheetnames==after.sheetnames
assert set(map(str,before.active.merged_cells.ranges))==set(map(str,after.active.merged_cells.ranges))
for row in before.active:
    for cell in row:
        assert after.active[cell.coordinate].value==expected.get(cell.coordinate,cell.value),cell.coordinate
assert after.active['C18'].value=='MSMF152L1G6'
assert [after.active[f'F{r}'].value for r in range(18,24)]==[2,2,4,4,2,2]
# 書込み前に、退避後の別編集がないことを確認する。
assert (folder/name).read_bytes()==(backup/name).read_bytes(),'ローカル依頼書が作業中に変更されました'
assert nas.read_bytes()==(backup/'NAS版'/name).read_bytes(),'NAS依頼書が作業中に変更されました'
assert (folder/eml_name).read_bytes()==(backup/eml_name).read_bytes(),'メール下書きが作業中に変更されました'
msg=EmailMessage(policy=email.policy.SMTP)
for key in ['From','To','Cc','Subject','X-Unsent','X-Identity-Key']:
    msg[key]=str(old[key])
msg['Message-ID']=make_msgid(domain='ime-group.co.jp')
msg.set_content(body)
payload=created.read_bytes()
msg.add_attachment(payload,maintype='application',subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename=name)
old_attachments=list(old.iter_attachments())
assert len(old_attachments)==2
image=old_attachments[1]
msg.add_attachment(image.get_payload(decode=True),maintype='image',subtype='png',filename=image.get_filename())
data=msg.as_bytes()
parsed=BytesParser(policy=email.policy.default).parsebytes(data)
assert parsed['X-Unsent']=='1'
for field in ['To','Cc']:
    assert {a.addr_spec for a in parsed[field].addresses}=={a.addr_spec for a in old[field].addresses}
attachments=list(parsed.iter_attachments())
assert len(attachments)==2 and attachments[0].get_payload(decode=True)==payload
assert attachments[1].get_payload(decode=True)==old_attachments[1].get_payload(decode=True)
shutil.copy2(created,folder/name)
shutil.copy2(created,nas)
with (folder/eml_name).open('wb') as f:f.write(data)
assert (folder/name).read_bytes()==nas.read_bytes()==payload
check=BytesParser(policy=email.policy.default).parsebytes((folder/eml_name).read_bytes())
assert list(check.iter_attachments())[0].get_payload(decode=True)==payload
print(json.dumps({'changed_cells':expected,'user_edits_preserved':True,'amp_and_qty_unchanged':True,'xlsx_sha256':hashlib.sha256(payload).hexdigest(),'eml':str(folder/eml_name),'backup':str(backup),'sent':False},ensure_ascii=False,indent=2))
