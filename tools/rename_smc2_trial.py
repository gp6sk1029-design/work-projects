"""smc2の宣言とソース参照を対応表で改名し、未検証の別名コピーを生成する。"""
import argparse
import collections
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
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('destination', type=Path)
args = parser.parse_args()
started = time.monotonic()
assert args.source.resolve() != args.destination.resolve(), '原本への書込みは禁止'
assert not args.destination.exists(), '既存ファイルへの上書きは禁止'
source_data = args.source.read_bytes()
source_hash = hashlib.sha256(source_data).hexdigest()
counts = collections.Counter()
changed_entries = []
preserved_entries = []

def decode_source(data):
    try:
        text = data.decode('utf-8-sig')
        return text if '\x00' not in text else None
    except UnicodeError:
        return None

def validate(text):
    stripped = text.lstrip()
    if stripped.startswith('<'):
        ET.fromstring(text)
    elif stripped.startswith('{'):
        for line in text.splitlines():
            if line.strip(): json.loads(line)

with zipfile.ZipFile(io.BytesIO(source_data)) as zin:
    assert zin.testzip() is None
    names = set()
    texts = {}
    for entry in zin.infolist():
        if entry.filename.endswith(('.xml', '.oem')):
            text = decode_source(zin.read(entry))
            if text is not None:
                validate(text)
                texts[entry.filename] = text
                if text.startswith('[SLWD'):
                    names.update(re.findall(r'(?:^|\t)N=([^\t\r\n]+)', text, re.M))
    mapping = {name: re.sub(r'(^|_)R(?=_|$)', r'\1A', name)
               for name in names if re.search(r'(^|_)R(?=_|$)', name)}
    assert mapping
    folded = {name.casefold() for name in names}
    assert not [(old, new) for old, new in mapping.items() if new.casefold() in folded], '変換先の名称重複'
    assert len({new.casefold() for new in mapping.values()}) == len(mapping), '変換による名称重複'
    pattern = re.compile(r'(?<![\w])(?:' + '|'.join(re.escape(n) for n in sorted(mapping, key=len, reverse=True)) + r')(?![\w])')
    def rename_match(match):
        counts[match[0]] += 1
        return mapping[match[0]]
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as zout:
        zout.comment = zin.comment
        for entry in zin.infolist():
            original = zin.read(entry)
            updated = original
            if entry.filename in texts:
                # 同じバイト数のASCII識別子だけを置換し、書式や改行を保持する。
                text = texts[entry.filename]
                updated_text = pattern.sub(rename_match, text)
                validate(updated_text)
                # ラダーのコメント文字列には変更を加えない。
                if text.lstrip().startswith('{'):
                    for old_line, new_line in zip(text.splitlines(), updated_text.splitlines()):
                        if old_line.strip():
                            old_obj, new_obj = json.loads(old_line), json.loads(new_line)
                            assert old_obj.get('CMT') == new_obj.get('CMT'), 'コメント変更を検出'
                # 端子割付・型・日本語コメントを含むN以外の定義は保持する。
                if text.startswith('[SLWD'):
                    for old_line, new_line in zip(text.splitlines(), updated_text.splitlines()):
                        old_fields = [f for f in old_line.split('\t') if not f.startswith('N=')]
                        new_fields = [f for f in new_line.split('\t') if not f.startswith('N=')]
                        assert old_fields == new_fields, '名称以外の変数定義変更を検出'
                updated = (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + updated_text.encode('utf-8')
                assert len(original) == len(updated)
            (changed_entries if original != updated else preserved_entries).append(entry.filename)
            zout.writestr(copy.copy(entry), updated)
    result = output.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as checked:
        assert checked.testzip() is None
        assert checked.namelist() == zin.namelist()
        for entry in zin.infolist():
            original, updated = zin.read(entry), checked.read(entry.filename)
            if entry.filename in preserved_entries: assert original == updated
            else:
                assert not pattern.search(decode_source(updated)), 'ソースに旧名称が残存'
    assert set(counts) == set(mapping), '変更されなかった対象変数あり'
    assert args.source.read_bytes() == source_data, '作業中に原本が変更された'
    # すべての事前検証が完了してから新規生成する。
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with args.destination.open('xb') as f: f.write(result)
    assert hashlib.sha256(args.destination.read_bytes()).hexdigest() == hashlib.sha256(result).hexdigest()
    report_dir = args.destination.parent / (args.destination.stem + '_確認資料')
    report_dir.mkdir(exist_ok=False)
    with (report_dir / '変数名変換一覧.csv').open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['変更前', '変更後', 'ソース内変更数'])
        writer.writerows((old, mapping[old], counts[old]) for old in sorted(mapping))
    summary = {
        '対象変数種類': len(mapping), '名称置換数': sum(counts.values()),
        '変更構成ファイル数': len(changed_entries), '不変構成ファイル数': len(preserved_entries),
        '原本SHA256': source_hash, '試作SHA256': hashlib.sha256(result).hexdigest(),
        '原本不変確認': hashlib.sha256(args.source.read_bytes()).hexdigest() == source_hash,
        'ZIP整合性': '確認済', 'XMLとラダーJSON構文': '確認済',
        'ソース内対象旧名称残存': 0, '変更後の既存名称との重複': 0,
        'SysmacStudio読込と全体再ビルド': '未実施・必須', '実機接続と転送': '未実施',
        'ビルド済データ': '変更せず保持。旧名称を含むため全体再ビルドが必要',
        '変更ファイル': changed_entries, '処理秒数': round(time.monotonic() - started, 2),
    }
    (report_dir / '検証結果.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (report_dir / '最初にお読みください.txt').write_text(
        'これはオフライン検証用の試作ファイルです。実機へ転送しないでください。\n'
        '原本・既存プロジェクトを上書きせず、別プロジェクトとして開いてください。\n'
        'Sysmac Studioの読込みは未確認です。開けた場合も全体を再ビルドしてください。\n'
        'ビルド済データ・検証情報は元のまま保持しており、旧名称を含みます。\n'
        '変数名変更により、タッチパネルや外部機器の名称参照へ影響する可能性があります。\n'
        '外部参照と実機の保持変数への影響も確認するまで、設備運転に使用しないでください。\n'
        '回路ロジック、端子割付、データ型、日本語コメントは変更していません。\n', encoding='utf-8-sig')
    print(json.dumps({k:v for k,v in summary.items() if k != '変更ファイル'}, ensure_ascii=False, indent=2))
    print('出力:', args.destination)
    print('確認資料:', report_dir)
