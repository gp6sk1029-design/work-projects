from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
import json,hashlib,os
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
assert m['native_read'] and m['comment_only']
p=Path(m['source']);stage=Path(m['staged']);raw=p.read_bytes();data=stage.read_bytes()
assert hashlib.sha256(raw).hexdigest()==m['source_sha256'] and hashlib.sha256(data).hexdigest()==m['output_sha256']
with ZipFile(p) as a,ZipFile(stage) as c:
    assert c.testzip() is None and a.namelist()==c.namelist()
    for part in a.namelist():
        if part!=m['part']:assert a.read(part)==c.read(part);continue
        ar=[json.loads(l) for l in a.read(part).decode('utf-8-sig').splitlines()]
        cr=[json.loads(l) for l in c.read(part).decode('utf-8-sig').splitlines()]
        assert len(ar)==len(cr)==45
        for x,y in zip(ar,cr):x.pop('CMT',None);y.pop('CMT',None);assert x==y
root=p.parent.resolve();history=(root/'履歴').resolve();archive=history/(p.stem+'_入出力表記変更前.smc2')
assert history.parent==root and archive.resolve().parent==history and not archive.exists()
assert stage.resolve().parent==b.resolve() and p.resolve().parent==root
history.mkdir(exist_ok=True)
with archive.open('xb') as f:f.write(raw)
assert archive.read_bytes()==raw
assert p.read_bytes()==raw
try:
    os.replace(stage,p);m['save_method']='同名置換'
except PermissionError:
    # アプリで開いている場合は、履歴確保後に同じファイルへ上書きする。
    with p.open('r+b') as f:f.write(data);f.truncate();f.flush();os.fsync(f.fileno())
    m['save_method']='同名上書き'
assert p.read_bytes()==data
m.update({'published':True,'archive':str(archive),'non_comment_fields_identical':True})
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/box-io-comment-20261105');out.mkdir(parents=True,exist_ok=True)
(out/'検証結果.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'変更内容・振り返り.txt').write_text(f'''H版の入出力コメント表記統一
実行日：2026-11-05
保存先：{p}
SHA256：{m['output_sha256']}
変更前：{archive}

【変更】
BoxPacking行間コメント{m['changed_rows']}行を「【Y番号】：名称」「【X番号】：名称」へ統一。
X1016/X1018は別行に分け、各センサー名と両方の確認条件を記載。
接点・コイル・結線・ST・数値・変数コメント・行数は変更なし。
全212内1エントリのCMTだけ変更、他211はバイト一致。
全CMT以外のフィールドは変更前と完全一致。メーカー同梱読込み45行失敗0。
実画面・全体ビルド・実機検証は今回実施していない。

【振り返りレポート】
エージェント名：生産技術主任補佐PDM_261102／Codex PLCコメント編集担当
業務・タスク内容：入出力番号のコメント書式統一・H同名上書き
実行日：2026-11-05
✅良かった点：番号と名称を統一形式にし、対になる入力を個別表示した。
⚠️改善点：番号表記の希望を初回からテンプレートへ反映する。
🔄次回試すこと：行間コメントのI/Oは最初から【番号】：名称を使用する。
📝SKILL.md更新提案：PLC行間コメントのI/O書式を【番号】：名称へ統一（該当PLC SKILL未存在のため提案のみ）。
💾MEMORY.md追記内容：H上書き、書式統一、コメント以外不変、変更前を履歴へ保存。
💰ROI評価：時間未計測・追加有料APIなし。{m['changed_rows']}行の表記を統一し、制御変更0に限定。
''',encoding='utf-8')
print(json.dumps({'output':str(p),'backup':str(archive),'changed_rows':m['changed_rows'],'sha256':m['output_sha256'],'published':True},ensure_ascii=False))
