"""Output_出力ラダーのPause参照だけをPause[1]へ変更する。"""
import argparse
import copy
import csv
import hashlib
import io
import json
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('destination', type=Path)
a = p.parse_args()
started = time.monotonic()
assert a.source.resolve() != a.destination.resolve()
assert not a.destination.exists(), '既存ファイルへの上書きは禁止'
report = a.destination.parent / (a.destination.stem + '_確認資料')
assert not report.exists(), '既存資料への上書きは禁止'
original = a.source.read_bytes()
sha = lambda b: hashlib.sha256(b).hexdigest()
pattern = re.compile(r'("Var"\s*:\s*")Pause(")')
logs = []
changed = []

def expected(obj):
    if isinstance(obj, dict): return {k: ('Pause[1]' if k == 'Var' and v == 'Pause' else expected(v)) for k,v in obj.items()}
    if isinstance(obj, list): return [expected(v) for v in obj]
    return obj

def pause_refs(obj):
    if isinstance(obj, dict):
        for k,v in obj.items():
            if k == 'Var' and isinstance(v, str) and re.search(r'(?<!\w)Pause(?!\w|\s*\[)', v): yield v
            yield from pause_refs(v)
    elif isinstance(obj, list):
        for v in obj: yield from pause_refs(v)

with zipfile.ZipFile(io.BytesIO(original)) as zin:
    assert zin.testzip() is None
    oem_path = next(e for e in zin.namelist() if e.endswith('.oem'))
    oem = zin.read(oem_path).decode('utf-8-sig')
    root = ET.fromstring(oem)
    targets = [e for e in root.iter() if e.attrib.get('type') == 'PouBody' and e.attrib.get('name') == 'Output_出力']
    assert len(targets) == 1, '対象ラダーが一意ではない'
    target_id = targets[0].attrib['id']
    target_path = next(e for e in zin.namelist() if e.endswith('/' + target_id + '.xml'))
    declarations = []
    for e in zin.namelist():
        if not e.endswith('.xml'): continue
        try: text = zin.read(e).decode('utf-8-sig')
        except UnicodeError: continue
        if text.startswith('[SLWD'):
            for line in text.splitlines():
                if re.search(r'(?:^|\t)N=Pause(?:\t|$)', line): declarations.append(line)
    assert declarations
    assert all('ARRAY[0..99] OF Bool'.casefold() in s.casefold() for s in declarations), '配列定義が想定と異なる'
    target_bytes = zin.read(target_path)
    target_text = target_bytes.decode('utf-8-sig')
    target_lines = target_text.splitlines(keepends=True)
    new_lines = []
    rung = 0
    for line_no, line in enumerate(target_lines, 1):
        if not line.strip(): new_lines.append(line); continue
        rung += 1
        before = json.loads(line)
        new, count = pattern.subn(r'\1Pause[1]\2', line)
        after = json.loads(new)
        assert expected(before) == after, '指定外の構造変更'
        assert not list(pause_refs(after)), '対象内に添字なしPause参照が残存'
        if count: logs.append((rung, line_no, count, before.get('CMT', '')))
        new_lines.append(new)
    total = sum(x[2] for x in logs)
    assert total > 0
    new_target = (b'\xef\xbb\xbf' if target_bytes.startswith(b'\xef\xbb\xbf') else b'') + ''.join(new_lines).encode('utf-8')
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as zout:
        zout.comment = zin.comment
        for e in zin.infolist():
            b = zin.read(e); new = b
            if e.filename == target_path: new = new_target
            elif e.filename.endswith(('.manifest', '.oem')):
                t = b.decode('utf-8-sig')
                if e.filename.endswith('.manifest'):
                    t, replacements = re.subn(r'(?<=solutionName=")[^"]*', lambda m: a.destination.stem, t)
                    assert replacements == 1
                else:
                    def tag(m):
                        tag_text = re.sub(r'(?<=\sname=")[^"]*', lambda n: a.destination.stem, m[0])
                        return re.sub(r'(?<=\sDN=")[^"]*', lambda n: a.destination.stem, tag_text)
                    t = re.sub(r'<Entity\b[^>]*\btype="Solution"[^>]*>', tag, t)
                ET.fromstring(t)
                new = (b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'') + t.encode('utf-8')
            if new != b: changed.append(e.filename)
            zout.writestr(copy.copy(e), new)
    result = output.getvalue()
    untouched_pause = 0
    with zipfile.ZipFile(io.BytesIO(result)) as checked:
        assert checked.testzip() is None
        assert checked.namelist() == zin.namelist()
        for e in zin.namelist():
            if e not in changed: assert checked.read(e) == zin.read(e)
            if e.endswith('.xml') and e != target_path:
                try: text = checked.read(e).decode('utf-8-sig')
                except UnicodeError: continue
                if text.startswith('{'):
                    for line in text.splitlines():
                        if line.strip(): untouched_pause += len(list(pause_refs(json.loads(line))))
        for old,new in zip(target_text.splitlines(), checked.read(target_path).decode('utf-8-sig').splitlines()):
            if old.strip(): assert expected(json.loads(old)) == json.loads(new)
    assert a.source.read_bytes() == original, '作業中に原本が変更された'
    with a.destination.open('xb') as f: f.write(result)
    assert a.destination.read_bytes() == result
    report.mkdir()
    with (report / '変更箇所一覧.csv').open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(['回路位置_1始まり','データ行番号','Pause変更数','回路コメント']); w.writerows(logs)
    summary = {
        '対象': 'IO_入出力 / Output_出力', '変更内容': 'Pause → Pause[1]',
        '変更箇所数': total, '変更回路数': len(logs), '配列定義': 'ARRAY[0..99] OF Bool',
        '対象ラダー内の添字なしPause残存': 0, '対象外ラダーの添字なしPause_未変更': untouched_pause,
        '原本SHA256': sha(original), '出力SHA256': sha(result), '原本不変': a.source.read_bytes() == original,
        '変数宣言とIO割付とコメント': '変更なし', '回路構造': 'Pause参照の添字追加以外は変更なし',
        '対象外不変構成ファイル数': len(zin.infolist()) - len(changed), '変更構成ファイル': changed,
        'ZIPと対象JSONとプロジェクト名XML': '整合性確認済',
        'SysmacStudio読み込みと全体再ビルド': '未実施・必須', '実機接続と転送': '未実施',
        '処理秒数': round(time.monotonic() - started, 2),
    }
    (report / '検証結果.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (report / '注意事項.txt').write_text(
        'Output_出力の添字なしPause参照だけをPause[1]に変更しました。\n'
        f'対象外ラダーに添字なしPauseが{untouched_pause}か所あります。今回は変更していません。\n'
        'Sysmac Studioでの読み込みと全体再ビルドは未実施です。設備に接続せず別プロジェクトとして確認してください。\n'
        'ビルド済みデータは原本のまま保持しています。全体再ビルドと動作確認を行うまで実機に転送しないでください。\n', encoding='utf-8-sig')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('保存先:', a.destination)
