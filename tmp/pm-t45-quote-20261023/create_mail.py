"""確認済み宛先を設定した未送信EMLを作成する。送信やmbox書込は行わない。"""
from pathlib import Path
from email.message import EmailMessage
from email.headerregistry import Address
from email import policy
from email.parser import BytesParser
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
message = EmailMessage(policy=policy.SMTP)
message["From"] = Address("幸田 祥平", addr_spec="sy-kouda@ime-group.co.jp")
message["To"] = Address("木村様【福西電機】", addr_spec="kimura.yuko@denzai.jp")
message["Cc"] = (
    Address("中村 智 次長", addr_spec="sa-nakamura@ime-group.co.jp"),
    Address("八木 工場長", addr_spec="a-yagi@ime-group.co.jp"),
    Address("藤本様【福西電機】", addr_spec="fujimoto.keita@denzai.jp"),
    Address("藤田さん【生産技術部】", addr_spec="ch-fujita@ime-group.co.jp"),
)
message["Subject"] = "見積依頼【マイクロフォトセンサ PM-T45／54台】"
message["X-Unsent"] = "1"
body = """福西電機株式会社
木村様

いつもお世話になっております。
一宮電機の幸田です。

下記製品のお見積りと納期をご回答いただけますでしょうか。

品名：マイクロフォトセンサ
型式：PM-T45
数量：54台

お手数をおかけいたしますが、よろしくお願いいたします。

株式会社一宮電機
生産技術部　幸田 祥平
"""
message.set_content(body, charset="utf-8")
destination = Path(r"C:\Users\SEIGI-N13\Desktop\福西電機_PM-T45_54台_見積依頼_未送信.eml")
with destination.open("xb") as stream:
    stream.write(message.as_bytes())
saved = BytesParser(policy=policy.default).parsebytes(destination.read_bytes())
assert [a.addr_spec for a in saved["To"].addresses] == ["kimura.yuko@denzai.jp"]
assert [a.addr_spec for a in saved["Cc"].addresses] == [
    "sa-nakamura@ime-group.co.jp", "a-yagi@ime-group.co.jp",
    "fujimoto.keita@denzai.jp", "ch-fujita@ime-group.co.jp",
]
assert saved["X-Unsent"] == "1"
assert all(value in saved.get_content() for value in ("PM-T45", "54台", "納期"))
assert not list(saved.iter_attachments())
print(json.dumps({"file": str(destination), "to": str(saved["To"]), "cc": str(saved["Cc"]),
                  "subject": str(saved["Subject"]), "unsent": True,
                  "thunderbird_drafts_saved": False}, ensure_ascii=False))
