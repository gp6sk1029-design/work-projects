"""閉じた内部Hのコメントだけを更新する。画面操作・PLC接続なし。"""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
import json,hashlib,os,stat
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
assert m['native_read']=='TOTAL=45 PARSE_FAIL=0 MODEL_FAIL=0' and not m['applied']
# ユーザーの直前回答を記録。経過時間やファイルロックの有無を承認・開閉確認の代用にしない。
m['project_closed_confirmation']=True
m['closed_confirmation_text']='ユーザー回答：Hは閉じていて、一覧画面になっている'
base=Path(m['internal_directory']).resolve();target=Path(m['target']).resolve()
assert base.parent==Path('C:/OMRON/Data/Solution').resolve() and target.parent==base
root=E.fromstring((base/(base.name+'.oem')).read_bytes())
assert next(e for e in root.iter() if e.get('type')=='Solution').get('name')==m['solution_name']
assert m['solution_name'].endswith('_20261105H')
original=target.read_bytes();replacement=Path(m['replacement']).read_bytes()
assert hashlib.sha256(original).hexdigest()==m['original_sha256']
assert hashlib.sha256(replacement).hexdigest()==m['replacement_sha256']
assert hashlib.sha256(Path(m['external_file']).read_bytes()).hexdigest()==m['external_sha256']
before=[json.loads(l) for l in original.decode('utf-8-sig').splitlines()]
after=[json.loads(l) for l in replacement.decode('utf-8-sig').splitlines()]
assert len(before)==len(after)==45
for a,c in zip(before,after):a.pop('CMT',None);c.pop('CMT',None);assert a==c
with ZipFile(m['backup']) as z:
    assert z.testzip() is None
    assert z.read(str(target.relative_to(base)).replace('\\','/'))==original
current={str(p.relative_to(base)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file()}
temp=base/(target.name+'.codex-comment-update.tmp')
assert temp.resolve().parent==base and not temp.exists()
with temp.open('xb') as f:f.write(replacement);f.flush();os.fsync(f.fileno())
os.chmod(temp,stat.S_IMODE(target.stat().st_mode))
assert target.read_bytes()==original
os.replace(temp,target)
assert target.read_bytes()==replacement
post={str(p.relative_to(base)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file()}
changed=[p for p in current if current[p]!=post.get(p)]
assert set(current)==set(post) and changed==[str(target.relative_to(base)).replace('\\','/')]
m.update({'applied':True,'internal_changed_files':changed,'non_comment_fields_identical':True,'ui_reflection_verified':False})
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
out=Path(m['backup']).parent
(out/'検証結果.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
report=f'''Sysmac内部Hへの直接コメント更新
2026-11-05／生産技術主任補佐PDM_261102・Codex PLC編集担当

【結論】
画面操作なしで、一覧内Hの内部ラダーデータ1ファイルを直接更新した。
.smc2を保存フォルダへ追加したのではなく、Hが参照するラダー本体のCMTを更新。
登録済みH：{m['solution_name']}
内部保存先：{base}
更新ファイル：{target}
変更後SHA256：{m['replacement_sha256']}

【実施前確認】
ユーザーが「Hは閉じていて、一覧画面になっている」と回答。
内部Hと外部Hの25ラダーセクションを比較。差分はBoxPackingコメント18行のみで制御差分なし。
内部H423ファイルを読み取り、以下へ完全バックアップしてSHA256を照合。
{m['backup']}

【実施内容・検証】
コメントを外部最新Hと同じ【Y番号】：名称／【X番号】：名称へ反映。
全423ファイルの更新前後ハッシュを比較し、変更は当該ラダー1ファイルだけ。
ラダー45行はCMT以外の全フィールド完全一致。接点・コイル・ST・数値・結線は変更なし。
修正案を同じ内部形式のまま検証用smc2へ入れ、同梱処理で45行解析/モデル化失敗0。
外部Hファイル、プロジェクト名、登録情報、他プロジェクト、更新日時メタデータは変更なし。
マウス/キーボード操作、インポート、アプリの保存操作、PLC接続・転送は行っていない。

【未検証】
Sysmac StudioでHを再度開いた際の実表示反映は未確認。
内部形式への直接書込みは、公式の保存API経由の更新ではない。
現段階で確認できたのは、本体ファイルの更新と同梱読込み検査まで。
一覧の更新日時は別メタデータのため、今回の直接更新では変更していない。
画面で開いたままのプロジェクトへ外部書込みする運用は、古いメモリ内容で上書きされる可能性があるため避ける。

【振り返りレポート】
エージェント名：生産技術主任補佐PDM_261102／Codex PLC編集担当
業務・タスク内容：画面操作なしで内部Hのコメントを直接反映する方式の検証
実行日：2026-11-05
✅良かった点
- 一覧内Hを名前で特定し、全25ラダーを照合して差分を18コメントに限定した。
- 閉じた状態をユーザーへ確認し、423ファイルのバックアップ後に1ファイルだけ更新した。
⚠️改善点
- 実画面の再読込みによる反映確認はまだ必要。
- ファイルを置くこと、内部本体の更新、アプリによる保存を区別して説明する。
🔄次回試すこと
- ユーザーのH再読込み結果で、表示が最新の【X1003】：コンテナ到着になったか確認する。
📝SKILL.md更新提案
- 内部直接更新は対象名/場所/差分/閉状態を確認し、完全バックアップ・非コメント差分0・更新後ハッシュを照合する。PLC SKILL未存在のため提案のみ。
💾MEMORY.md追記内容
- H内部フォルダ、直接更新1ファイル、18コメント、423ファイルバックアップ、表示未確認を記録。
💰ROI評価
- 投じた時間・コスト：時間未計測、追加有料APIなし。
- 得られたリターン：今回の18コメント反映で、画面操作と手動インポートを0回にできた。
- 次回改善でROIを上げる方法：アプリ再読込み確認後、閉じた同一プロジェクトへの限定更新手順として再利用する。

【公式資料と今回の調査の区別】
保存フォルダの公式案内：
https://store.omron.com.au/knowledge-base/sysmac-project-directory
この資料は保存先の説明であり、内部ファイルを直接書き換える方法の公式保証ではない。
内部形式・差分・書込み結果は今回のローカル調査で確認した。
'''
(out/'直接更新の結果・振り返り.txt').write_text(report,encoding='utf-8')
print(json.dumps({'applied':True,'internal_project':m['solution_name'],'target':str(target),'changed_comment_rows':18,'changed_files':len(changed),'backup':m['backup'],'ui_reflection_verified':False},ensure_ascii=False))
