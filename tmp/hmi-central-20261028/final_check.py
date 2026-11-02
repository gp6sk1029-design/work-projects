"""保存直前の追加照合と、検証範囲の記録。"""
import hashlib
import json
import zipfile
import build_h as b

report = json.loads(b.REPORT.read_text(encoding='utf-8-sig'))
assert hashlib.sha256(b.SOURCE.read_bytes()).hexdigest() == report['source_sha256']
assert hashlib.sha256(b.STAGED.read_bytes()).hexdigest() == report['output_sha256']
with zipfile.ZipFile(b.SOURCE) as old, zipfile.ZipFile(b.STAGED) as new:
    assert old.namelist() == new.namelist()
    assert new.testzip() is None
    changed = [name for name in old.namelist() if old.read(name) != new.read(name)]
    assert sorted(changed) == sorted(report['changed_entries'])
    # タスク順、OEMツリー、インラインSTの実体、HMI画面ファイルは全て保持。
    for name in old.namelist():
        if name.endswith(('.oem', '.dat')) or name == report['names']['task']:
            assert old.read(name) == new.read(name)
    for key in ('error', 'fh', 'output'):
        assert 'HMI_MessageNo' not in new.read(report['names'][key]).decode('utf-8-sig')
report['checks']['task_oem_inline_st_and_screen_files_byte_preserved'] = True
report['checks']['message_number_reads_only_in_original_hmi_text_conversion'] = True
report['editor_section_loader'] = {
    'available': False,
    'reason': 'アプリの実行環境が必要。原本G/生成HともCompactLadderPersisterのコンストラクタで同じNullReferenceException。',
    'not_treated_as_a_successful_editor_load': True,
}
report['verification_scope'] = '各行のメーカー変換・変数読込み・独自モデル。Sysmac全体ビルド/画面表示/タイマー実時間/実機動作は未確認。'
b.REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('最終照合：変更9エントリ、既存タスク/OEM/インラインST/画面を保持、表示番号書込みはHMIのみ')
