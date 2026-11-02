"""smc2のコメントのみを同時置換し、原本と回路を保持して別名保存する。"""
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
assert not a.destination.exists(), '既存ファイルへの上書きは禁止'
report = a.destination.parent / (a.destination.stem + '_確認資料')
assert not report.exists(), '既存確認資料への上書きは禁止'
mapping = {'A(右側)': 'A(左側)', 'B(左側)': 'B(右側)'}
pattern = re.compile('|'.join(re.escape(s) for s in mapping))
counts = collections.Counter()
log = []
changed = []

def comment(text, category, path):
    matches = pattern.findall(text)
    new = pattern.sub(lambda m: mapping[m[0]], text)
    if new != text:
        counts[category + '_変更項目数'] += 1
        counts[category + '_置換数'] += len(matches)
        counts.update(matches)
        log.append((path, category, text, new))
    return new

def st_segments(text):
    # ST文字列は保持し、行・入れ子ブロックコメントを識別する。
    i = start = 0
    segments = []
    while i < len(text):
        if text[i] in "'\"":
            q = text[i]; i += 1
            while i < len(text):
                if text[i] == '$': i += 2; continue
                if text[i] == q:
                    if i + 1 < len(text) and text[i+1] == q: i += 2; continue
                    i += 1; break
                i += 1
        elif text.startswith('//', i) or text.startswith('(*', i):
            segments.append(('code', text[start:i]))
            begin = i
            if text.startswith('//', i):
                while i < len(text) and text[i] not in '\r\n': i += 1
            else:
                depth = 1; i += 2
                while i < len(text) and depth:
                    if text.startswith('(*', i): depth += 1; i += 2
                    elif text.startswith('*)', i): depth -= 1; i += 2
                    else: i += 1
                assert depth == 0, 'STコメントの閉じ忘れ'
            segments.append(('comment', text[begin:i])); start = i
        else: i += 1
    segments.append(('code', text[start:]))
    return segments

def mask_json(obj):
    if isinstance(obj, dict):
        return {k: ([(kind, value if kind == 'code' else '<コメント>') for kind, value in st_segments(v)] if k == 'TXT' else mask_json(v)) for k,v in obj.items() if k != 'CMT'}
    if isinstance(obj, list): return [mask_json(v) for v in obj]
    return obj

def decode(b):
    try:
        text = b.decode('utf-8-sig')
        return text if '\x00' not in text else None
    except UnicodeError: return None

def validate(text):
    if text.lstrip().startswith('<'): ET.fromstring(text)
    elif text.lstrip().startswith('{'):
        for line in text.splitlines():
            if line.strip(): json.loads(line)

json_pair = re.compile(r'("(?P<key>[^"\\]+)"\s*:\s*)(?P<value>"(?:[^"\\]|\\.)*")')
def transform(text, path):
    if text.startswith('[SLWD'):
        text = re.sub(r'(?<=\t)Com=([^\t\r\n]*)', lambda m: 'Com=' + comment(m[1], '変数コメント', path), text)
        text = re.sub(r'(?<=\t)EC=([^\t\r\n]*)', lambda m: 'EC=' + re.sub(r'(\bC=")([^"]*)(")', lambda c: c[1] + comment(c[2], '配列要素コメント', path) + c[3], m[1]), text)
    elif text.lstrip().startswith('{'):
        def pair(m):
            if m['key'] not in ('CMT', 'TXT'): return m[0]
            value = json.loads(m['value'])
            if m['key'] == 'CMT': new = comment(value, '回路コメント', path)
            else:
                new = ''.join(comment(s, 'STコメント', path) if kind == 'comment' else s for kind,s in st_segments(value))
            return m[1] + json.dumps(new, ensure_ascii=False) if new != value else m[0]
        text = json_pair.sub(pair, text)
    return text

def mask_slwd(text):
    text = re.sub(r'(?<=\t)Com=[^\t\r\n]*', 'Com=<コメント>', text)
    return re.sub(r'(?<=\t)EC=([^\t\r\n]*)', lambda m: 'EC=' + re.sub(r'(\bC=")[^"]*(")', r'\1<コメント>\2', m[1]), text)

original = a.source.read_bytes()
sha = lambda data: hashlib.sha256(data).hexdigest()
output = io.BytesIO()
with zipfile.ZipFile(io.BytesIO(original)) as zin:
    assert zin.testzip() is None
    with zipfile.ZipFile(output, 'w') as zout:
        zout.comment = zin.comment
        for e in zin.infolist():
            b = zin.read(e); updated = b
            if e.filename.endswith(('.xml', '.oem', '.manifest')):
                t = decode(b)
                if t is not None:
                    validate(t)
                    new = transform(t, e.filename)
                    if t.startswith('[SLWD'):
                        assert mask_slwd(t) == mask_slwd(new), '変数名・型・割付・設定の変更を検出'
                    elif t.lstrip().startswith('{'):
                        assert len(t.splitlines()) == len(new.splitlines())
                        for x,y in zip(t.splitlines(), new.splitlines()):
                            if x.strip(): assert mask_json(json.loads(x)) == mask_json(json.loads(y)), '回路条件・構造の変更を検出'
                    if e.filename.endswith('.manifest'):
                        new = new.replace('solutionName="' + a.source.stem + '"', 'solutionName="' + a.destination.stem + '"')
                    elif e.filename.endswith('.oem'):
                        def tag(m):
                            return m[0].replace('name="' + a.source.stem + '"', 'name="' + a.destination.stem + '"').replace('DN="' + a.source.stem + '"', 'DN="' + a.destination.stem + '"')
                        new = re.sub(r'<Entity\b[^>]*\btype="Solution"[^>]*>', tag, new)
                    validate(new)
                    updated = (b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'') + new.encode('utf-8')
            if b != updated: changed.append(e.filename)
            zout.writestr(copy.copy(e), updated)
    result = output.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as checked:
        assert checked.testzip() is None
        assert checked.namelist() == zin.namelist()
        for e in zin.infolist():
            b = checked.read(e.filename)
            if e.filename not in changed: assert b == zin.read(e)
            if e.filename.endswith(('.xml', '.oem', '.manifest')):
                t = decode(b)
                if t is not None:
                    validate(t)
                    assert transform(t, e.filename) == t, '旧指定表記がコメントに残存'
        manifest = next(decode(checked.read(e)) for e in checked.namelist() if e.endswith('.manifest'))
        assert 'solutionName="' + a.destination.stem + '"' in manifest
    assert a.source.read_bytes() == original, '作業中に元ファイルが変更された'
    with a.destination.open('xb') as f: f.write(result)
    assert a.destination.read_bytes() == result
    report.mkdir()
    with (report / 'コメント変更一覧.csv').open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(['構成ファイル','分類','変更前','変更後']); w.writerows(log)
    summary = {
        '変更ルール': mapping, '変更件数': dict(counts),
        'コメント変更項目数': len(log), '変更構成ファイル数': len(changed),
        '対象外不変構成ファイル数': len(zin.infolist()) - len(changed),
        '変数名と型とIO割付と保持設定': 'B版と同一', '回路構成と条件とST実行コード': 'B版と同一',
        '元ファイルSHA256': sha(original), '出力SHA256': sha(result),
        '元ファイル不変': a.source.read_bytes() == original,
        '旧指定表記のコメント内残存': 0, 'ZIPとXMLとJSON': '整合性確認済',
        '内部プロジェクト名': a.destination.stem,
        'SysmacStudio読込みと全体再ビルド': '未実施・必須', '実機接続と転送': '未実施',
        '処理秒数': round(time.monotonic() - started, 2),
    }
    (report / '検証結果.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (report / '注意事項.txt').write_text(
        'コメントと回路コメントだけをA(左側)・B(右側)へ更新しました。変数名はB版から変更していません。\n'
        '設備に接続せず、既存プロジェクトを上書きしない形で読み込み、全体を再ビルドしてください。\n'
        '生成済みビルドデータは元のままです。外部機器の変数参照と保持変数への影響も確認するまで実機へ転送しないでください。\n', encoding='utf-8-sig')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('保存先:', a.destination)
