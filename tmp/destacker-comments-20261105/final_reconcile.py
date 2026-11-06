"""コメント同期・日時整合・重複版の不変を照合し、記録を残す。"""
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as E
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;w=b/'reconcile';out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-comments-20261105/reconcile')
m=json.loads((w/'meta.json').read_text(encoding='utf-8'));before=json.loads((b/'copy_audit.json').read_text(encoding='utf-8'))
p=sm.Project(m['internal']);f=sm.Project(m['external']);reference=sm.Project(b/'I_all_comments.smc2')
assert f.fingerprint==json.loads((w/'native.json').read_text(encoding='utf-8-sig'))['sha256']
assert not sm.comparison(p,f)['control_difference'] and p.declarations()==f.declarations()
assert all(a['rows']==c['rows'] for a,c in sm.align(p,f))
for q in (p,f):
    for part in reference.variable_parts:
        name=PurePosixPath(part).name;hits=[v for k,v in q.entries.items() if PurePosixPath(k).name==name]
        assert hits==[reference.entries[part]]
    oem=next(k for k in q.entries if k.endswith('.oem'))
    root=E.fromstring(q.entries[str(PurePosixPath(oem).with_suffix('.xml'))])
    assert root.find('.//DateModified').text==m['iso_jst']
    assert root.find('.//Project').text==m['solution']
unchanged=[]
for entry in before['projects']:
    if entry['directory']==str(p.path):continue
    current=sm.Project(entry['directory']);assert current.fingerprint==entry['sha'];unchanged.append(entry['name'])
r=json.loads((out/'内部日時更新結果.json').read_text(encoding='utf-8'))
r.update({'list_timestamp_display_verified':True,'list_timestamp_user_response':'20:30になった','external_synced':str(f.path),'external_sha':f.fingerprint,'all_25_ladders_equal':True,'all_variable_definitions_equal':True,'all_variable_comment_tables_equal':True,'duplicate_projects_unchanged':unchanged,'native_rows':1375,'native_failures':0,'full_application_build':False,'plc_transfer':False})
sm.save_json(out/'最終確認.json',r)
report='''【修正結果】
対象：登録済み無印20261105Iと、Codex編集用内の外部I.smc2。
コメント表示はユーザーが「開始条件」を確認済み。
最終更新日時は2026/11/05 20:30へ整合し、Sysmac再起動後にユーザーが「20:30になった」と確認。

原因：直接編集したコメントは読み込まれたが、一覧用SolutionModel.DateModifiedとOEM dateLastModifiedが14:39のままだった。アプリの変更状態にはならず、通常保存が無効だった。外部I.smc2にもコメントを同期していなかった。
対策：閉じた一覧状態を画像確認、内部423ファイルを完全バックアップし、日時メタデータ2ファイルだけ更新。他421ファイルはバイト単位で不変。外部Iはコメント4ファイル・日時等のメタデータ2ファイルを更新し、206ファイルは不変。上書き前外部Iは同フォルダの履歴へ保管。
全25ラダー・変数定義は内部と外部で一致。変数説明表も一致。I_1～I_3はハッシュ不変。制御・時間設定・入出力・軸許可・PLC転送は変更なし。
同梱読込み検査1375行、失敗0。全体ビルド・実機動作の確認とは区別する。公式保存APIで保存したものではない。

【振り返りレポート】
エージェント名：生産技術主任補佐PDM_261102／Codex PLCコメント編集担当
業務・タスク内容：コメント反映の再確認と、一覧更新日時・外部Iの整合修正
実行日：2026-11-05

✅ 良かった点
- コメントの実表示と更新日時の実表示を、それぞれユーザー回答で確認した。
- 内部2ファイルだけの更新を全423ファイルのハッシュで確認。制御差分0を維持した。

⚠️ 改善点
- 初回の直接更新で、一覧日時と外部Iへの同期を一緒に扱わず混乱を生んだ。
- 同名に近いI_1～I_3の存在も含め、対象識別と反映範囲を先に示すべきだった。

🔄 次回試すこと
- コメント・変数説明・外部ファイル・一覧日時の4項目を一組として完了確認する。

📝 SKILL.md更新提案
- 該当セクション：内部プロジェクト／直接反映
- 変更内容：内容更新と日時更新を区別し、日時整合を求められた場合はSolutionModel.DateModifiedとOEM dateLastModifiedだけを完全バックアップ・差分限定で更新する。再起動後の一覧表示まで確認し、外部SMC2への同期状況を明記する。アプリの通常保存とは呼ばない。

💾 MEMORY.md追記内容
- カテゴリ：Sysmac直接コメント更新の完了確認
- 内容：無印Iのコメント表示と再起動後20:30の日時をユーザーが確認。内部日時2項目と外部Iを同期し、制御と変数定義の差分0、複製3版不変を照合。

💰 ROI評価
- 投じた時間・コスト：作業時間は未計測。追加有料APIなし。
- 得られたリターン：対象1版を内外で統一。再インポート時に旧コメントへ戻る経路1件を解消。制御差分0。
- 次回改善でROIを上げる方法：反映範囲4項目の事前確認で、再確認と重複インポートの手間を減らす。
'''
(out/'日時とファイル同期・振り返り.txt').write_text(report,encoding='utf-8')
memory=Path('C:/Users/SEIGI-N13/work-projects/MEMORY.md')
entry='''
### 2026-11-05 無印Iのコメント反映・一覧日時・外部SMC2を整合（Codex PLCコメント編集担当）
- ユーザーが無印Iの【開始条件】表示を確認。Ctrl+Sは保存無効。直接編集はアプリの変更状態を作らず、一覧のSolutionModel.DateModifiedとOEM dateLastModifiedが旧14:39のままだった。内部コメントと一覧日時を別に検証する。
- Sky画像で一覧の閉状態を直前確認し、内部423ファイル完全バックアップ後に無印Iの日時2ファイルだけを2026/11/05 20:30へ整合。他421ファイル不変。GUID・作成日時・その他情報は保持。前d6291985→後b39252a9。通常のアプリ保存ではない。
- 外部Iにもコメント4ファイルとメタデータ2ファイルを同期し、旧Iを履歴へ保存。全212中206不変、SHA a7df246e967f3cc8b33e9e9aada56801778badd10e9fc152e37fd3b867e5e2ff。全25節・変数定義と説明表は内部と一致。複製I_1～I_3は不変。1375行同梱検査失敗0、制御変更・PLC操作なし。
- Sysmac再起動後ユーザーが「20:30になった」と回答。コメント・日時とも実表示確認済み。成果物outputs/destacker-comments-20261105/reconcile/最終確認.json、日時とファイル同期・振り返り.txt。SKILL提案：直接更新の完了はコメント/変数説明/外部ファイル/一覧日時を一組で確認し、未対応範囲を先に明記。時間未計測・追加有料APIなし。
'''
with memory.open('a',encoding='utf-8') as stream:stream.write(entry)
print(json.dumps({'verified':True,'internal_changed_files':2,'external_control_difference':0,'duplicate_projects_unchanged':len(unchanged),'comment_and_timestamp_display_verified':True,'report':str(out/'日時とファイル同期・振り返り.txt')},ensure_ascii=False))
