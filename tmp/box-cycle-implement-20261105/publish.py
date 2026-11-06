"""検証済みG版を保存し、変更前Fを同フォルダの履歴へ移す。"""
from pathlib import Path
from zipfile import ZipFile
import json,hashlib,os,shutil
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
for key,file in [('native_validation','native.json'),('independent_audit','audit.json'),('condition_validation','conditions.json'),('rcon_condition_validation','rcon_conditions.json')]:
    m[key]=json.loads((b/file).read_text(encoding='utf-8'))
assert 'MISSING=0 PARSE_MODEL_FAIL=0' in m['native_validation']['connections']
assert m['independent_audit']['box_coils_sequential_1_to_49']
assert len(m['condition_validation']['machines'])==32 and len(m['rcon_condition_validation']['axes'])==4
src=Path(m['source']);dest=Path(m['output']);stage=Path(m['staged'])
root=src.parent.resolve();assert dest.resolve().parent==root
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
data=stage.read_bytes();assert hashlib.sha256(data).hexdigest()==m['output_sha256']
history=(root/'履歴').resolve();assert history.parent==root
archive=history/src.name
if archive.exists():archive=history/(src.stem+'_変更前_'+m['source_sha256'][:10]+src.suffix)
assert archive.resolve().parent==history and archive.resolve().is_relative_to(root) and not archive.exists()
assert not dest.exists()
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/box-cycle-implement-20261105');out.mkdir(parents=True,exist_ok=True)
backup=out/(src.stem+'_変更前.smc2')
assert not backup.exists()
with backup.open('xb') as f:f.write(src.read_bytes())
with dest.open('xb') as f:f.write(data)
assert dest.read_bytes()==data
history.mkdir(exist_ok=True)
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source_sha256']
try:
    os.rename(src,archive);m['archived']=True;m['original_retained_due_to_lock']=False
except OSError as exc:
    # 開いているFを強制終了しない。履歴コピーを確保し、原本が残ったことを報告する。
    if archive.exists():raise
    with archive.open('xb') as f:f.write(src.read_bytes())
    m['archived']=False;m['original_retained_due_to_lock']=True;m['archive_error']=str(exc)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['source_sha256']
m['archive']=str(archive);m['backup']=str(backup);m['published']=True
with ZipFile(dest) as z:assert z.testzip() is None
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'検証結果.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
report=f'''修正版G 作成結果・検証・振り返り
2026-11-05／生産技術主任補佐PDM_261102・Codex PLC編集担当

【保存先】
{dest}
G SHA256：{m['output_sha256']}
変更前F：{archive}
F SHA256：{m['source_sha256']}
履歴へ移動：{m['archived']}／ロックによる原本残置：{m['original_retained_due_to_lock']}
作業用バックアップ：{backup}

【反映内容】
1. BoxPackingの初回完了をM[2]へ。旧M[2]～[48]はM[3]～[49]へ全参照を改番。
   初回開始枝にInit_Busy・M[2]の否定接点を置き、M[1]自己保持は迂回。
   M[2]は取出し先判定へ受渡した後に自己保持し、通常完了や次箱で解除しない。
   初回状態判定と初回方向判定の自己保持も、初回完了後に解除する。
2. 取出し判定の共通否定接点をA/B Busyへ。Busyに受渡すまで選択を維持。
3. A側のチャック行完了後、箱詰めZ軸が上昇完了した時点でBoxPacking_A_Pickup_Done。
   ST7 A31行の3枝合流後に同信号の共通否定接点を追加し、取出し待ちを解除。
4. 箱内XY合流の開始元を、すでに落ちる取出し後Z上昇工程から、合流まで保持する箱内Y移動工程へ変更。
5. 箱内配置後のZ上昇完了ONで入数判定。80個未満は取出し選択へ、80個は排出へ。
6. 満杯排出後、コンテナ軸が受渡位置へ戻り完了した立上りでBox_Total_CTを0へ。
7. 前回の100ms完了を今回の完了と誤認しないよう、コンテナ設置・取出し後Z上昇・箱内配置後Z上昇の開始枝は旧MoveDoneのOFFを待つ。自己保持枝は迂回。
8. 行コメントを#大工程・中工程・分岐合流へ整理。X/Yは信号名、RCON2は軸名を明記。
   BoxPacking_M[1]～[49]に短い要素コメントを設定。Y軸位置設定[1]の既存B側誤記をA側へ。

【X1003の扱い：ユーザー確認済み】
HMI_RCON2_5_OUT_TargetPos[2]（設置）・[3]（排出）では感知しない。
この2位置の初回判定へX1003を追加していない。位置[1]の受渡到着確認は従来どおり。

【RCON2_2～5：追加指示による接続】
対象は箱詰めX・Y・Z・コンテナ軸。RCON1とRCON2_1、出力セクションは不変。
数値設定4種の転送をP_Onで接続し、現在位置などの入力監視はDataValid時に更新。
既存100msのTON/TOF・Up方式を維持し、新規STや20ms処理は追加していない。
既存M[3]の予備ビットへ自動開始許可を割当て。
  自動モード、非一時停止、非非常停止、非リセット、既存の通信・配置・軸更新・運転許可、
  入力有効・数値変換OK・軸準備完了、正の速度/加減速・非負の位置決め幅で許可。
StartのTOF後も許可を確認し、許可OFF時に内部Startを解除する。
要求受付はMoveDone中に入力TONをリセットし、次の保持要求を完了解除後に取り直す。
既存M[2]の予備ビットへ「今回移動のPEND OFF確認」を割当て。
開始保持中にPEND OFFを記憶し、その後のPEND ONでのみDoneを生成する。
通信変換ST6行、I/O配置、設定値、タイマー時間、許可フラグの初期値は変更なし。

【新しい名前の変数：2個】
BoxPacking_Init_Busy：初回コンテナ確認中／BOOL・非保持・共通主POUローカル。
BoxPacking_A_Pickup_Done：A側取出し・Z退避完了／BOOL・非保持・ST7とBoxで共用。
初回完了は新規Init_Done名ではなく、指定のBoxPacking_M[2]。
RCONは既存配列の未使用M[2]/M[3]を使用。AutoMode外部参照をRCON POUへ追加。

【主な行番号：G版・0始まり】
BoxPacking：0 初回開始／1 初回完了保持M2／2 初回Busy／3 初回状態判定。
6 初回方向判定／10 コンテナ設置入口／15 取出し先判定／16 A側Busy。
29 取出し後Z上昇／30 A取出し完了／31 X箱内位置／32 Y箱内位置。
35 箱内XY合流／38 配置後Z上昇／39 入数判定／40～44 満杯排出・戻り・CT0。
ST7 A：31 取出し待ち保持の共通解除。
RCON2_2：283 自動開始許可／289 Start／322 開始保持／323 PEND OFF確認／324 Done。
RCON2_3：325 自動開始許可／331 Start／364 開始保持／365 PEND OFF確認／366 Done。
RCON2_4：367 自動開始許可／373 Start／406 開始保持／407 PEND OFF確認／408 Done。
RCON2_5：409 自動開始許可／415 Start／448 開始保持／449 PEND OFF確認／450 Done。

【検証結果】
全212エントリ中6変更、206不変。Box45行、ST7 A32行、RCON457行。
メーカー同梱処理：全1367行の読込み・モデル化失敗0。1591コイルの接続欠落0。
M[1]～[49]の通常コイルは各1か所、欠番・重複なし。既存ST本文・座標・識別子を保持。
ST7待ち16組合せ、A完了8組合せ、Z上昇完了6組合せ、CTリセット3状態を検査。
A側の2箱80個＋次箱5個まで32条件ケース。計64箱・1056回の取出し開始を条件モデルで確認。
  初期位置4種、完了遅延2種、次製品準備3種の24ケース、および完了保持付き8ケース。
RCON4軸：許可条件17件/軸、受付保持8組合せ/軸、PEND初期ONの誤完了防止、
  要求ORが切れない切替、内部StartのPause即時遮断を10ms刻み条件モデルで確認。
Box側モデルは完了入力を外部供給し、RCON側モデルは別に検査。両者と実通信の結合検証は未実施。

【現時点で未確認の内容】
実機の通信・単軸動作は未確認とのユーザー回答。
RCON2_CommOK・MotionPermit等を作る処理は本F版には見当たらない。
通信正常、I/O割付とバイト順、軸更新・運転許可、速度/加減速/幅/位置の設定は、実機情報での確認が必要。
本修正はこれらのフラグをTRUE固定して実機を動かすものではない。
既存の出力反映STは許可OFF時に前値を保持するため、内部Startの解除は実機停止保証ではない。
全体リビルド、PLCシミュレーター、実機波形・原点・干渉・PLC転送は未実施。
B側は未作成の指定に従い、新規動作や動作検証を実施していない。既存Box内B参照は共通改番のみ整合。

【資料】
IAI公式RCONフィールドネットワーク リファレンスマニュアル：
https://www.iai-robot.co.jp/download/reference/pdf/REFERENCE_RCON_FN%28MJ0473%29.pdf
直接数値・フル直値で必要な設定データとDSTRによる位置決めの説明を参照。
実機のモード・マニュアル版と既存通信配置の適合確認は未実施。

【振り返りレポート】
エージェント名：生産技術主任補佐PDM_261102／Codex PLC編集担当
業務・タスク内容：初回・取出し受渡し・80個繰返し・RCON経路・コメントの反映
実行日：2026-11-05
✅ 良かった点
- X1003の検出範囲を確認し、設置・排出位置への誤った条件追加を避けた。
- 関連4行だけでなくBox45行とST7待ちの受渡しを検査し、XY合流元の矛盾も修正できた。
- 既存STと100ms方式を保持し、許可フラグの固定ONを避けてRCONをラダーで接続した。
⚠️ 改善点
- 前の部分モデルではXY合流・ST7の生成解除まで検査できていなかった。今回は範囲を明記して検査を追加した。
- PowerShell5のUTF-8スクリプト直読で文字化けしたため、UTF-8指定のScriptBlock読込みへ修正した。
- 実通信・単軸動作・全体ビルドは未確認であり、条件モデルの合格と区別する必要がある。
🔄 次回試すこと
- 実機I/Oと単軸PEND/Start波形を確認した情報を基に、通信正常・軸許可の作成条件を確定する。
📝 SKILL.md更新提案
- 該当PLC SKILL.mdは未存在。準備信号の生成～再生成、XY合流の前工程保持、Done保持中の次要求を検査項目へ追加する提案。
💾 MEMORY.md追記内容
- G版の変更範囲、ユーザー回答、検証件数、実機未確認、許可値を固定ONにしない方針、履歴を記録。
💰 ROI評価
- 投じた時間・コスト：実測時間未計測。追加有料APIなし。
- 得られたリターン：49工程コメントと改番を照合し、32ケース・4軸条件を再検査可能にした。
- 次回改善でROIを上げる方法：実機で確認できた信号・タイミングを検査条件へ取り込み、同じ連続運転の手戻りを減らす。
'''
(out/'変更内容・検証・振り返り.txt').write_text(report,encoding='utf-8')
# コメント一覧も生成物から取り出し、現行の行番号に追従させる。
with ZipFile(dest) as z:
    rs=[json.loads(l) for l in z.read(m['box_part']).decode('utf-8-sig').splitlines()]
(out/'G版_BoxPacking行コメント一覧.txt').write_text('\n\n'.join(str(i)+'行\n'+r.get('CMT','') for i,r in enumerate(rs)),encoding='utf-8')
print(json.dumps({'output':str(dest),'archive':str(archive),'archived':m['archived'],'original_remains':m['original_retained_due_to_lock'],'sha256':m['output_sha256'],'report':str(out/'変更内容・検証・振り返り.txt')},ensure_ascii=False))
