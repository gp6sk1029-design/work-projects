"""同梱読み込み処理で検証済みの出力修正をCへ反映する。"""
from pathlib import Path
from zipfile import ZipFile
import hashlib,json,shutil,sys,tempfile
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).parent
source=base/'output_repaired_nativecheck_20261023.smc2'
dest=next(Path(r'C:\Users\SEIGI-N13\Desktop').glob('3089-2603A_*_20261023C.smc2'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old_hash='e09c4681e30b39a9b635ba045c9fb610aeb6a8699c5c8f684de8677c02580009'
new_hash='2c8cee0b432eb824fde0bd8bd5974a290f091126ebb263d7a7a91a92453a41c9'
assert sha(source)==new_hash and sha(dest)==old_hash,'確認したファイル以外は上書きしない'
with ZipFile(dest) as old,ZipFile(source) as new:
    assert old.namelist()==new.namelist() and new.testzip() is None
    changed=[n for n in old.namelist() if old.read(n)!=new.read(n)]
    assert len(changed)==1 and changed[0].endswith('09c1f70b-b9ac-4e5d-884f-9779e69a597a.xml')
    output=changed[0]
    a=[json.loads(l) for l in old.read(output).decode('utf-8-sig').splitlines()]
    b=[json.loads(l) for l in new.read(output).decode('utf-8-sig').splitlines()]
    assert len(a)==len(b)==316
    changed_rows=[i for i,(left,right) in enumerate(zip(a,b)) if left!=right]
    assert changed_rows==[88,94,97,184,190,193,196,202,205]
    for suffix in ['a6a85ff3-f6aa-4c8c-a49b-ae9f1e045ba8.xml','4bc99ae0-7ace-4891-a17a-c3fe2079278d.xml']:
        name=next(n for n in old.namelist() if n.endswith(suffix))
        assert old.read(name)==new.read(name)
backup=Path(tempfile.mkdtemp(prefix='C版_出力表示修正前_20261023_',dir=dest.parent))
for f in [dest,dest.with_suffix('.変更内容.txt'),dest.with_suffix('.変数一覧.txt'),dest.with_suffix('.検証結果.json')]:
    if f.exists():shutil.copy2(f,backup/f.name)
assert sha(backup/dest.name)==old_hash
with tempfile.NamedTemporaryFile(prefix='verified_output_',suffix='.smc2',dir=dest.parent,delete=False) as f:stage=Path(f.name)
shutil.copy2(source,stage);assert sha(stage)==new_hash
stage.replace(dest);assert sha(dest)==new_hash
with ZipFile(dest) as z:
    assert z.testzip() is None
    assert len(z.read(output).decode('utf-8-sig').splitlines())==316
result={'日付':'2026-10-23','C版':str(dest),'上書き前退避先':str(backup),
    '旧C版SHA256':old_hash,'修正C版SHA256':new_hash,'変更エントリ':changed,
    '変更した出力行':changed_rows,'不変エントリ数':190,
    '原因':'入力枝追加時に右側の並列コイルも下げて接続が途切れ、9行のモデル変換が失敗。内部参照番号も再整合。',
    '同梱読み込み処理_旧C':'出力316行中9行でモデル変換失敗',
    '同梱読み込み処理_修正C':'出力316行、構文失敗0・モデル変換失敗0',
    '同梱読み込み処理_原点復帰':'28行、構文失敗0・モデル変換失敗0',
    '原点復帰28行・モータ処理':'元Cと全バイト一致',
    'Sysmac画面表示・全体再ビルド':'未確認（前ターンの画面操作は利用者が停止）',
    'PLC接続・転送':'なし'}
dest.with_suffix('.検証結果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
notes=['C版 出力セクションの読み込み不具合修正','2026-10-23','修正C版：'+str(dest),
    '上書き前バックアップ：'+str(backup),'',
    '【原因と修正】',result['原因'],
    '右側の並列コイルと縦線を元の位置へ戻し、入力側の枝だけに原点復帰接点とUpを追加する形へ修正。',
    '部品・左右母線・連続縦線の内部参照番号も正常な構成へ合わせた。',
    '出力行88/94/97/184/190/193/196/202/205のみを修正。全316行を保持。',
    '追加9個と既存3個の原点復帰用出力接点、およびIO外部変数9件は保持。',
    '原点復帰の28行、モータ処理、グローバル変数、I/O割付、機器設定は変更なし。',
    '共通開始・リセット・Busy/Done集約などの制御方式変更は追加していない。','',
    '【今回追加したメーカー処理による検証】',
    'Sysmac同梱NexProgramming.dllのCompactRungToStringConverterとCompactRungToNormalRungConverterを使用。',
    '旧Cでは追加9行のモデル変換が失敗することを再現。',
    '修正Cの出力316行は構文/モデル変換とも失敗0。原点復帰28行も失敗0。',
    'この確認はメーカーのラダー変換処理を使った読込み検証であり、GUI表示・全体ビルド・実機動作の確認とは別。',
    '前ターンのWindows画面操作は利用者がEsc停止したため、今回は画面操作を再開していない。',
    'Sysmacで現在開いているプロジェクトが自動更新されるわけではないので、この修正C版を再インポートする。',
    '使用前に全体再ビルドと出力セクションの表示を確認する。PLC接続・転送なし。','',
    '旧C SHA256：'+old_hash,'修正C SHA256：'+new_hash]
dest.with_suffix('.変更内容.txt').write_text('\n'.join(notes)+'\n',encoding='utf-8-sig')
(base/'output_repair_published_20261023.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
