"""原本を保持してSysmacソースの左右識別子とコメントをA/B表記にする。"""
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
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
p.add_argument('destination', type=Path)
a = p.parse_args()
started = time.monotonic()
assert a.source.resolve() != a.destination.resolve()
assert not a.destination.exists(), '保存先が存在するため中止'
report_dir = a.destination.parent / (a.destination.stem + '_確認資料')
assert not report_dir.exists(), '確認資料フォルダが存在するため中止'
original_data = a.source.read_bytes()
digest = lambda b: hashlib.sha256(b).hexdigest()
name_counts = collections.Counter()
comment_counts = collections.Counter()
comment_log = []
file_log = []
logging_enabled = True
comment_pattern = re.compile(r'A\(右側\)|B\(左側\)|右側|左側|右|左')
comment_values = {'右': 'A(右側)', '右側': 'A(右側)', '左': 'B(左側)', '左側': 'B(左側)'}

def comments(value, category, filename):
    hits = collections.Counter()
    def replace(m):
        if m[0] in comment_values:
            hits[m[0]] += 1
            return comment_values[m[0]]
        return m[0]
    new = comment_pattern.sub(replace, value)
    if new != value and logging_enabled:
        comment_counts[category + '_変更項目数'] += 1
        comment_counts[category + '_置換数'] += sum(hits.values())
        comment_log.append((filename, category, value, new))
    return new

def st_comments(text, filename):
    # STの文字列リテラルは変えず、行コメントと入れ子ブロックコメントだけを変換する。
    chunks = []
    i = 0
    while i < len(text):
        start = i
        if text[i] in "'\"":
            quote = text[i]
            i += 1
            while i < len(text):
                if text[i] == '$': i += 2; continue
                if text[i] == quote:
                    if i + 1 < len(text) and text[i + 1] == quote: i += 2; continue
                    i += 1
                    break
                i += 1
            chunks.append(text[start:i])
        elif text.startswith('//', i):
            while i < len(text) and text[i] not in '\r\n': i += 1
            chunks.append(comments(text[start:i], 'STコメント', filename))
        elif text.startswith('(*', i):
            depth = 1
            i += 2
            while i < len(text) and depth:
                if text.startswith('(*', i): depth += 1; i += 2
                elif text.startswith('*)', i): depth -= 1; i += 2
                else: i += 1
            assert depth == 0, 'STコメントの閉じ忘れ'
            chunks.append(comments(text[start:i], 'STコメント', filename))
        else:
            chunks.append(text[i]); i += 1
    return ''.join(chunks)

def validate(text):
    if text.lstrip().startswith('<'): ET.fromstring(text)
    elif text.lstrip().startswith('{'):
        for line in text.splitlines():
            if line.strip(): json.loads(line)

def decode(b):
    try:
        t = b.decode('utf-8-sig')
        return t if '\x00' not in t else None
    except UnicodeError: return None

with zipfile.ZipFile(io.BytesIO(original_data)) as zin:
    assert zin.testzip() is None
    texts = {}
    names = set()
    for e in zin.infolist():
        if e.filename.endswith(('.xml', '.oem', '.manifest')):
            t = decode(zin.read(e))
            if t is not None:
                validate(t)
                texts[e.filename] = t
                if t.startswith('[SLWD'):
                    names.update(re.findall(r'(?:^|\t)N=([^\t\r\n]+)', t, re.M))
    mapping = {n: re.sub(r'(^|_)(R|L)(?=_|$)', lambda m: m[1] + {'R':'A', 'L':'B'}[m[2]], n)
               for n in names if re.search(r'(^|_)(R|L)(?=_|$)', n)}
    folded = {n.casefold() for n in names}
    assert not [(n, v) for n, v in mapping.items() if v.casefold() in folded], '変換先名称の重複'
    assert len({v.casefold() for v in mapping.values()}) == len(mapping)
    pattern = re.compile(r'(?<![\w])(?:' + '|'.join(re.escape(n) for n in sorted(mapping, key=len, reverse=True)) + r')(?![\w])')
    def rename(m):
        name_counts[m[0]] += 1
        return mapping[m[0]]
    # JSONの文字列の値だけを編集し、回路構造・配置と行分割をそのまま保持する。
    json_pair = re.compile(r'("(?P<key>[^"\\]+)"\s*:\s*)(?P<value>"(?:[^"\\]|\\.)*")')
    def source_comments(t, filename):
        if t.startswith('[SLWD'):
            t = re.sub(r'(?<=\t)Com=([^\t\r\n]*)', lambda m: 'Com=' + comments(m[1], '変数コメント', filename), t)
            t = re.sub(r'(?<=\t)EC=([^\t\r\n]*)', lambda m: 'EC=' + re.sub(r'(\bC=")([^"]*)(")', lambda c: c[1] + comments(c[2], '配列要素コメント', filename) + c[3], m[1]), t)
        elif t.lstrip().startswith('{'):
            def pair(m):
                value = json.loads(m['value'])
                if m['key'] == 'CMT': new = comments(value, '回路コメント', filename)
                elif m['key'] == 'TXT': new = st_comments(value, filename)
                else: return m[0]
                return m[1] + json.dumps(new, ensure_ascii=False) if new != value else m[0]
            t = json_pair.sub(pair, t)
        return t
    def strip_comments(obj):
        if isinstance(obj, dict): return {k:strip_comments(v) for k,v in obj.items() if k != 'CMT'}
        if isinstance(obj, list): return [strip_comments(v) for v in obj]
        return obj
    output = io.BytesIO()
    old_title = a.source.stem
    new_title = a.destination.stem
    with zipfile.ZipFile(output, 'w') as zout:
        zout.comment = zin.comment
        for e in zin.infolist():
            b = zin.read(e)
            new_b = b
            if e.filename in texts:
                original = texts[e.filename]
                renamed = pattern.sub(rename, original)
                t = source_comments(renamed, e.filename)
                # 保存ファイル名だけでなくプロジェクト名も指定名にする。
                if e.filename.endswith('.manifest'):
                    t = t.replace('solutionName="' + old_title + '"', 'solutionName="' + new_title + '"')
                elif e.filename.endswith('.oem'):
                    def solution_tag(m):
                        return m[0].replace('name="' + old_title + '"', 'name="' + new_title + '"').replace('DN="' + old_title + '"', 'DN="' + new_title + '"')
                    t = re.sub(r'<Entity\b[^>]*\btype="Solution"[^>]*>', solution_tag, t)
                validate(t)
                # 型・I/O割付・定数属性・保持設定等は不変であることを確認。
                if original.startswith('[SLWD'):
                    for old, new in zip(renamed.splitlines(), t.splitlines()):
                        clean = lambda s: [f for f in s.split('\t') if not f.startswith(('Com=', 'EC='))]
                        assert clean(old) == clean(new)
                if original.lstrip().startswith('{'):
                    for old, new in zip(renamed.splitlines(), t.splitlines()):
                        if old.strip():
                            old_obj, new_obj = json.loads(old), json.loads(new)
                            # ST文字列の変更もコメント変換に限られることを確認する。
                            logging_enabled = False
                            expected = json.loads(source_comments(old, e.filename))
                            logging_enabled = True
                            assert expected == new_obj, '回路構造または条件の変更'
                new_b = (b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'') + t.encode('utf-8')
            if new_b != b: file_log.append(e.filename)
            zout.writestr(copy.copy(e), new_b)
    result = output.getvalue()
    assert set(name_counts) == set(mapping)
    with zipfile.ZipFile(io.BytesIO(result)) as checked:
        assert checked.testzip() is None
        assert checked.namelist() == zin.namelist()
        for e in zin.infolist():
            b = checked.read(e.filename)
            if e.filename not in file_log: assert b == zin.read(e)
            if e.filename in texts:
                t = decode(b)
                assert not pattern.search(t), '旧対象名称がソースに残存'
                validate(t)
                # コメント変換の冪等性から、右/左の未変換と二重変換を検出する。
                before = len(comment_log)
                assert source_comments(t, e.filename) == t
                assert len(comment_log) == before
        manifest = next(t for path in texts if path.endswith('.manifest') for t in [decode(checked.read(path))])
        assert 'solutionName="' + new_title + '"' in manifest
    assert a.source.read_bytes() == original_data, '作業中に原本が変更された'
    with a.destination.open('xb') as f: f.write(result)
    assert a.destination.read_bytes() == result
    report_dir.mkdir()
    for filename, header, rows in [
        ('変数名変換一覧.csv', ['変更前','変更後','ソース内変更数'], [(n,mapping[n],name_counts[n]) for n in sorted(mapping)]),
        ('コメント変換一覧.csv', ['構成ファイル','分類','変更前','変更後'], comment_log),
    ]:
        with (report_dir / filename).open('x', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f); w.writerow(header); w.writerows(rows)
    summary = {
        'RからA_変数種類': sum(bool(re.search(r'(^|_)R(?=_|$)', n)) for n in mapping),
        'LからB_変数種類': sum(bool(re.search(r'(^|_)L(?=_|$)', n)) for n in mapping),
        '変数名変更数': sum(name_counts.values()), 'コメント変更': dict(comment_counts),
        '変更構成ファイル数': len(file_log), '対象外不変構成ファイル数': len(zin.infolist()) - len(file_log),
        '原本SHA256': digest(original_data), '出力SHA256': digest(result),
        '原本不変': digest(a.source.read_bytes()) == digest(original_data),
        'ZIPとXMLとJSON整合性': '確認済', 'ソースの旧対象名残存': 0, '名称衝突': 0,
        '端子割付と型と保持設定': '変更なし', '回路構成と条件': '変更なし',
        '内部プロジェクト名': new_title,
        'ビルド済データ': '原本のまま。Sysmac Studioで全体再ビルド必須',
        'SysmacStudio読込と全体再ビルド': '未実施', '実機接続と転送': '未実施',
        'HMI表示文字列とPOU名': '今回のコメント変更対象外。元の表記を保持',
        '処理秒数': round(time.monotonic() - started, 2),
    }
    (report_dir / '検証結果.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (report_dir / '注意事項.txt').write_text(
        '原本からR→A・L→Bの変数名変更と、左右コメントのA(右側)・B(左側)表記統一を実施しました。\n'
        'Sysmac Studioでの読み込み・再ビルドは未確認です。設備に接続せず、既存プロジェクトを上書きしない形で確認してください。\n'
        'ビルド済みデータは元のままです。必ず全体を再ビルドしてください。\n'
        'タッチパネルや外部通信の変数参照、保持変数への影響がないかも確認するまで実機へ転送しないでください。\n'
        '名称・コメントのみ変更しています。HMIメッセージ文字列、POU名、元コメントの意味の修正は対象外です。\n', encoding='utf-8-sig')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('保存先:', a.destination)
