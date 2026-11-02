from pathlib import Path
import email.policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formataddr,make_msgid
import json
import shutil
import hashlib
import sys
from openpyxl import load_workbook

sys.stdout.reconfigure(encoding='utf-8')
work=Path(__file__).parent
design=json.loads((work/'edits.json').read_text(encoding='utf-8'))
filename=design['filename']
generated=Path(r'C:\Users\SEIGI-N13\work-projects\outputs\quote-fukunishi-20261019')/filename
nas=Path(r'\\nas-ime5\生産技術部\2.見積 決裁願\見積\1_見積依頼書\2026')/filename
folder=Path(r'C:\Users\SEIGI-N13\Desktop\巻線機オーバーホール_福西電機見積依頼_20261019')
eml=folder/'見積依頼メール_福西電機様_未送信.eml'
source_image=Path(r'C:\Users\SEIGI-~1\AppData\Local\Temp\codex-clipboard-f81079ce-b3c4-412a-a0b7-a3a13441cc2b.png')
image_name='旧A4モータ仕様_数量2・4・2.png'
before=load_workbook(work.parent/'quote-20261019'/'template.xlsx')
after=load_workbook(generated)
assert before.sheetnames==after.sheetnames==['原紙']
assert set(map(str,before.active.merged_cells.ranges))==set(map(str,after.active.merged_cells.ranges))
for row in before.active:
    for cell in row:
        assert after.active[cell.coordinate].value==design['edits'].get(cell.coordinate,cell.value),cell.coordinate
for address,value in design['edits'].items():
    assert after.active[address].value==value,address
assert [after.active[f'F{r}'].value for r in range(18,24)]==[2,2,4,4,2,2]
assert sum(after.active[f'F{r}'].value for r in [18,20,22])==8
assert sum(after.active[f'F{r}'].value for r in [19,21,23])==8
assert after.active['B8'].value=='希望納期：'
if nas.exists() or eml.exists():
    raise FileExistsError('同名成果物の上書きを防ぐため停止します。')
assert source_image.is_file()

body='''福西電機 株式会社
藤本様　木村様

いつも大変お世話になります。
一宮電機の幸田です。

巻線機オーバーホールに伴う新規制御部品として、
パナソニック製サーボモータ・サーボアンプの見積依頼書を送付させていただきます。

以前いただいた下記お見積りを参考にしております。
・2026年8月6日付「パナソニック製品(サーボモータ)」
・お見積番号：QT08020260806-203557

今回は、添付の旧A4シリーズの仕様・数量に合わせ、下記A6シリーズを候補としました。
制御方式は、同案件のSLM-8000からのパルス列による位置制御を予定しております。

【見積依頼候補】
1. 旧モータ：MSMA152S1G（1.5kW、キー溝、ブレーキなし）
   モータ：MSMF152L1G6　2台
   アンプ：MDDLT55SF　2台
   条件：200V、3000r/min、キー溝・オイルシールあり、ブレーキなし

2. 旧モータ：MSMD022S1A（200W、ストレート軸、ブレーキなし）
   モータ：MSMF022L1A2　4台
   アンプ：MADLT15SF　4台
   条件：200V、3000r/min、ストレート軸、ブレーキ・オイルシールなし、リード線タイプ

3. 旧モータ：MSMD042S1B（400W、ストレート軸、ブレーキ付き）
   モータ：MSMF042L1B2　2台
   アンプ：MBDLT25SF　2台
   条件：200V、3000r/min、ストレート軸、保持ブレーキ付き、オイルシールなし、リード線タイプ

数量は添付画像の2台・4台・2台を全体数量とし、モータ計8台・アンプ計8台です。
前回のお見積りにあった750W品は、今回の対象には含めておりません。

【仕様・選定についての確認のお願い】
・上記候補のモータとアンプの組合せ、および旧A4からの置換可否をご確認ください。
・特に容量、キー溝／ストレート軸、保持ブレーキ、オイルシールの条件を優先してください。
・200W・400Wは旧品に合わせてリード線タイプを候補としています。
  コネクタタイプ等への変更をご提案いただく場合は、相違点もお知らせください。
・取付フランジ、軸径・軸長、キー溝寸法、取付穴・インロー、本体長さ等の
  機械的な差異と、必要な改造・注意点をご教示ください。
・パルス列入力対応のA6SF系を候補としていますが、SLM-8000との接続に必要な
  信号方式・電圧・周波数条件、電子ギヤ等の設定条件もご確認をお願いいたします。
・旧品は17bit、新候補は23bitエンコーダのため、既存設定や配線の流用可否、
  再設定・調整が必要な点をご教示ください。旧A4アンプとの混用は想定しておりません。
・動力・エンコーダ・ブレーキ・制御用のケーブル／コネクタ、24Vブレーキ電源、
  回生抵抗やセーフティ接続等について、必要な付属品の型式・数量・仕様条件と
  価格を別項目でご提示ください。ケーブル長は未確定のため、必要条件をお知らせください。
・候補より適切な製品がある場合は、旧品との相違点を添えてご提案ください。

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
notes='''選定・照合メモ（2026年10月19日確認）

用途：巻線機オーバーホール／SLM-8000からパルス列位置制御を予定。
これは見積依頼用の一次選定であり、完全な差し替え互換や実機動作を保証するものではありません。

【数量】
ユーザー添付画像の数量2・4・2を総数として使用。2台分として再乗算していません。
1.5kW 2組、200W 4組、400W保持ブレーキ付き2組。モータ8台、アンプ8台。

【候補と根拠】
MSMA152S1G → MSMF152L1G6 ＋ MDDLT55SF
旧／新とも200V・1.5kW・3000r/min・100mm角・キー溝・オイルシール有・ブレーキ無。
新モータのメーカー「適用アンプ」にMDDLT55SFが載り、パルス列入力対応。

MSMD022S1A → MSMF022L1A2 ＋ MADLT15SF
旧／新とも200V・200W・3000r/min・60mm角・丸軸・リード線・ブレーキ無・オイルシール無。
新モータのメーカー「適用アンプ」にMADLT15SFが載り、パルス列入力対応。

MSMD042S1B → MSMF042L1B2 ＋ MBDLT25SF
旧／新とも200V・400W・3000r/min・60mm角・丸軸・リード線・保持ブレーキ有・オイルシール無。
新モータのメーカー「適用アンプ」にMBDLT25SFが載り、パルス列入力対応。

【前回の福西電機見積との関係】
2026/8/6、No.QT08020260806-203557。
前回モータMSMF042L1S1（400W・キー付タップ付・ブレーキ無）は今回400W丸軸ブレーキ有の条件と不一致。
前回MSMF082L1S1は750Wのため今回200W/1.5kW用へ流用しない。
前回MBDLT25SFは今回400Wモータの適用表にあり再選定可。
前回MCDLT35SFは今回の3モータの適用アンプとして採用していない。
前回の見積単価は転記していません。

【メーカー資料と推論の区別】
メーカーが公表する容量・軸仕様・ブレーキ・適用アンプを照合して上記候補を選びました。
旧品と新品の完全互換をメーカーが認定したという意味ではありません。
MSMD旧品の現行WebページにはA5/A4共用品と明記されています。
旧17bit→新23bitで、エンコーダ・慣性・本体形状・配線・調整条件は同一とみなしません。
200W・400Wはリード線タイプ末尾2を採用し、前回コネクタ型末尾1との違いを明示。
キー溝仕様とキー付タップ仕様を同義として扱っていません。
メーカー適用表に載ることはモータ／アンプ間の適合で、SLM-8000や機械への適合を保証しません。
実機電源、取付寸法・軸寸法、負荷、信号電圧・周波数、電子ギヤ、STO等の安全回路、
ブレーキの保持機能、配線・ケーブル長と必要付属品を販売店／設計担当で確認してください。
保持ブレーキを運転中の制動用途には使用しません。
依頼書中の「B有／B無」は保持ブレーキの有無です。
CCは同じ案件のため前回と同じ中村智次長・八木工場長としています。
希望納期は未指定で空欄。送信・発注はしていません。

【公式出典：仕様欄／適用アンプ欄】
旧1.5kW：https://industry.panasonic.com/global/en/products/motor/fa-motor/ac-servo/number/msma152s1g
旧200W：https://industry.panasonic.com/global/en/products/motor/fa-motor/ac-servo/number/msmd022s1a
旧400W：https://industry.panasonic.com/jp/ja/products/motor/fa-motor/ac-servo/number/msmd042s1b
新1.5kW：https://industry.panasonic.com/global/en/products/motor/fa-motor/ac-servo/number/msmf152l1g6
新200W：https://industry.panasonic.com/global/en/products/motor/fa-motor/ac-servo/number/msmf022l1a2
新400W：https://industry.panasonic.com/global/en/products/motor/fa-motor/ac-servo/number/msmf042l1b2
前回400W：https://industry.panasonic.com/jp/ja/products/motor/fa-motor/ac-servo/number/msmf042l1s1
アンプ例：https://industry.panasonic.com/jp/ja/products/motor/fa-motor/ac-servo_driver/number/madlt15sf
'''
msg=EmailMessage(policy=email.policy.SMTP)
msg['From']=formataddr(('幸田 祥平','sy-kouda@ime-group.co.jp'))
msg['To']=', '.join([formataddr(('福西電機 藤本様','fujimoto.keita@denzai.jp')),formataddr(('福西電機 木村様','kimura.yuko@denzai.jp'))])
msg['Cc']=', '.join([formataddr(('中村 智 次長','sa-nakamura@ime-group.co.jp')),formataddr(('八木 工場長','a-yagi@ime-group.co.jp'))])
msg['Subject']='見積依頼書の送付【巻線機オーバーホール／サーボモータ・アンプ】'
msg['X-Unsent']='1'
msg['X-Identity-Key']='id1'
msg['Message-ID']=make_msgid(domain='ime-group.co.jp')
msg.set_content(body)
payload=generated.read_bytes()
msg.add_attachment(payload,maintype='application',subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename=filename)
imagebytes=source_image.read_bytes()
msg.add_attachment(imagebytes,maintype='image',subtype='png',filename=image_name)
folder.mkdir(parents=True,exist_ok=True)
shutil.copy2(generated,nas)
shutil.copy2(generated,folder/filename)
shutil.copy2(source_image,folder/image_name)
with eml.open('xb') as f:f.write(msg.as_bytes())
(folder/'メール本文_確認用.txt').write_text(body,encoding='utf-8-sig')
(folder/'選定根拠・旧品との相違点.txt').write_text(notes,encoding='utf-8-sig')
parsed=BytesParser(policy=email.policy.default).parsebytes(eml.read_bytes())
assert parsed['X-Unsent']=='1'
assert {a.addr_spec for a in parsed['To'].addresses}=={'fujimoto.keita@denzai.jp','kimura.yuko@denzai.jp'}
assert {a.addr_spec for a in parsed['Cc'].addresses}=={'sa-nakamura@ime-group.co.jp','a-yagi@ime-group.co.jp'}
attached=list(parsed.iter_attachments())
assert len(attached)==2
assert attached[0].get_payload(decode=True)==payload
assert attached[1].get_payload(decode=True)==imagebytes
assert nas.read_bytes()==payload
print(json.dumps({'xlsx':str(nas),'eml':str(eml),'folder':str(folder),'motor_qty':8,'amp_qty':8,'attachments':2,'xlsx_sha256':hashlib.sha256(payload).hexdigest(),'sent':False},ensure_ascii=False,indent=2))
