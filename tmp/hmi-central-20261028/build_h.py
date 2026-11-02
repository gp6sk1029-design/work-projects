"""HMIの位置を変えず、メッセージ番号選択をHMIへ集約する。実機は操作しない。"""
from pathlib import Path
import collections
import copy
import hashlib
import importlib.util
import itertools
import json
import random
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
BASE = Path(__file__).resolve().parent
OLD_BASE = BASE.parent / 'error-station-20261028'
spec = importlib.util.spec_from_file_location('station_helpers', OLD_BASE / 'build_g.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
PREVIOUS = json.loads((OLD_BASE / 'verification.json').read_text(encoding='utf-8-sig'))
SOURCE = Path(PREVIOUS['destination'])
DEST = SOURCE.with_name(SOURCE.name.replace('20261029G', '20261029H'))
STAGED = BASE / DEST.name
REPORT = BASE / 'verification.json'
SUFFIXES = {
    'error': '78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml',
    'output': '09c1f70b-b9ac-4e5d-884f-9779e69a597a.xml',
    'fh': 'fdce7b3c-0b49-4708-9024-8a98fe6b24b5.xml',
    'hmi': '2b857527-a5b5-49c0-9233-e70f3ae89ba1.xml',
    'globals': 'f07dd06c-505c-431b-b9fc-098949805b4e.xml',
    'mode_vars': 'b530d740-9d69-41c3-974a-97c06e823eb2.xml',
    'other_vars': 'a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml',
    'io_vars': '9576fedf-9472-4ce6-b9ed-6eda5b4f0514.xml',
    'metadata': '20a6b651-4c34-401a-965e-db3e18414d5c.xml',
    'task': 'e2e4c044-641e-49ac-a486-71b29b0e7c87.xml',
}
REQUEST = 'HMI_Message_Request'
PRIORITY = list(range(1, 101)) + [108, 109, 116, 117, 110, 121, 111, 112] + list(range(101, 108)) + [113, 114, 115, 118, 119, 120]


def request(number):
    return f'{REQUEST}[{number}]'


def message_number(c):
    if c.get('Name') != 'MOVE' or not any(p.get('Var') == 'HMI_MessageNo[0]' for p in c.get('Out', [])):
        return None
    value = next(p['Var'] for p in c['In'] if p.get('Arg') == 'In')
    assert re.fullmatch(r'INT#\d+', value), value
    return int(value[4:])


def normalize(row):
    """Ixだけを採番し直す。既存UpのIdは保持する。空VLsも必ず明示する。"""
    row.setdefault('VLs', [])
    ix = 0
    for c in row['CLs']:
        for node in h.walk(c):
            if node.get('__type') in ('LD', 'ST', 'F', 'FB', 'PRM', 'IST'):
                node['Ix'] = ix
                ix += 1
    row['LRI'], row['RRI'] = ix, ix + 1
    # 同じXの連続する縦線は同じIxとする。
    previous = None
    wire_ix = ix + 1
    seen = set()
    for v in sorted(row['VLs'], key=lambda w: (w.get('X', 0), w.get('Y', 0))):
        xy = (v.get('X', 0), v.get('Y', 0))
        assert xy not in seen, ('縦線重複', xy)
        seen.add(xy)
        if previous is None or xy != (previous[0], previous[1] + 1):
            wire_ix += 1
        v['Ix'] = wire_ix
        previous = xy
    coords = [(c.get('X', 0), c.get('Y', 0)) for c in row['CLs']]
    assert len(coords) == len(set(coords)), coords
    return row


def capture_messages(original, raw_fh=False):
    """表示MOVEの通電を通常コイルへ記録。他の命令・パルス・配線は維持する。"""
    row = copy.deepcopy(original)
    number_cells = [(c, message_number(c)) for c in row['CLs'] if message_number(c) is not None]
    assert number_cells
    # FHエラーの表示抑制はHMI内の代入順へ置換する。
    if raw_fh:
        number = number_cells[0][1]
        trigger = next(c['Var'] for c in row['CLs'] if c.get('__type') == 'LD' and c.get('Var') != 'Error_Common_MessageActive')
        return h.dnf([[h.ld(trigger)]], [h.st(request(number))], '表示要求：' + str(number)), [(number, False)]
    insertions = []
    # 下から処理し、元の同一行上の後続処理を分岐の上側に保持する。
    for cell, number in sorted(number_cells, key=lambda p: (p[0].get('Y', 0), p[0].get('X', 0)), reverse=True):
        x, y = cell.get('X', 0), cell.get('Y', 0)
        has_following = any(c is not cell and c.get('Y', 0) == y and c.get('X', 0) > x and c['__type'] != 'HL' for c in row['CLs'])
        index = row['CLs'].index(cell)
        if not has_following:
            row['CLs'][index] = dict(h.st(request(number)), X=x, Y=y)
        else:
            assert x > 0
            # MOVEが途中にある場合、主経路をHLへ置換し、直下の枝に表示要求だけ追加。
            # 下側の既存行と縦線を1段ずらし、元の接続は切らない。
            row['CLs'][index] = {'__type': 'HL', 'X': x, 'Y': y}
            for c in row['CLs']:
                if c.get('Y', 0) > y:
                    c['Y'] = c.get('Y', 0) + 1
            added = []
            for v in row['VLs']:
                if v.get('Y', 0) > y:
                    v['Y'] = v.get('Y', 0) + 1
                elif v.get('Y', 0) == y:
                    added.append({**v, 'Y': y + 1})
            row['VLs'] += added
            if not any(v.get('X', 0) == x and v.get('Y', 0) == y for v in row['VLs']):
                row['VLs'].append({'X': x, 'Y': y, 'Ix': -1})
            row['CLs'].append(dict(h.st(request(number)), X=x, Y=y + 1))
        insertions.append((number, has_following))
    return normalize(row), insertions


def sig(c):
    """配置・採番を除く、元の命令とパラメータ。"""
    result = copy.deepcopy(c)
    for node in h.walk(result):
        for key in ('Ix', 'X', 'Y'):
            node.pop(key, None)
    return json.dumps(result, ensure_ascii=False, sort_keys=True)


def semantic_power(row, values):
    """配線の限定ブール検査。タイマーQ/比較/Upは固定した外部結果として与える。"""
    graph = collections.defaultdict(list)
    max_y = max([c.get('Y', 0) for c in row['CLs']] + [v.get('Y', 0) + 1 for v in row.get('VLs', [])])
    for c in row['CLs']:
        kind = c['__type']
        x, y = c.get('X', 0), c.get('Y', 0)
        condition = True
        if kind == 'LD':
            condition = values.get('VAR:' + c['Var'], False)
            if c.get('Not'):
                condition = not condition
        elif kind == 'FB':
            condition = values.get('FB:' + c.get('Var', ''), False)
        elif kind == 'F' and c.get('Name') == 'Up':
            condition = values.get('UP:' + c['Id'], False)
        elif kind == 'F' and c.get('PL'):
            condition = values.get('CMP:' + sig(c), False)
        # コイル/命令は左から右へ。右側に命令がない枝の出力点も記録する。
        if condition:
            graph[(x, y)].append((x + 1, y))
    for v in row.get('VLs', []):
        a = (v.get('X', 0), v.get('Y', 0)); b = (a[0], a[1] + 1)
        graph[a].append(b); graph[b].append(a)
    reached = {(0, y) for y in range(max_y + 1)}
    queue = list(reached)
    while queue:
        for to in graph[queue.pop()]:
            if to not in reached:
                reached.add(to); queue.append(to)
    return reached


def keys_for(row):
    keys = set()
    for c in row['CLs']:
        if c['__type'] == 'LD':
            keys.add('VAR:' + c['Var'])
        elif c['__type'] == 'FB':
            keys.add('FB:' + c.get('Var', ''))
        elif c['__type'] == 'F' and c.get('Name') == 'Up':
            keys.add('UP:' + c['Id'])
        elif c['__type'] == 'F' and c.get('PL'):
            keys.add('CMP:' + sig(c))
    return sorted(keys)


def build():
    assert not DEST.exists(), '既存H版は上書きしません'
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert source_hash == PREVIOUS['output_sha256'], 'G版が更新されています。調査をやり直してください'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        raw = {n: z.read(n) for n in z.namelist()}
        infos, archive_comment = z.infolist(), z.comment
    texts = {}
    ladders = {}
    for name, data in raw.items():
        try:
            t = data.decode('utf-8-sig')
        except UnicodeError:
            continue
        if '\x00' in t:
            continue
        texts[name] = t
        if t.lstrip().startswith('{'):
            try:
                rr = [json.loads(l) for l in t.splitlines() if l.strip()]
            except json.JSONDecodeError:
                continue
            if rr and all('CLs' in r for r in rr):
                ladders[name] = rr
    names = {key: next(n for n in texts if n.endswith(suffix)) for key, suffix in SUFFIXES.items()}
    assert sorted(PRIORITY) == list(range(1, 122))
    changes = {}
    new_ladders = dict(ladders)
    replacements = []
    tests = []
    comments = {}
    globals_before = h.declarations(texts[names['globals']])
    # 各セクションは同じ場所・同じ順序で実行。表示の発生時点だけを記録する。
    for scope in ('error', 'fh', 'output'):
        name = names[scope]
        rr = []
        for i, row in enumerate(ladders[name]):
            if any(c.get('Var') == 'Error_Common_MessageActive' and c.get('__type') == 'ST' for c in row['CLs']):
                assert scope == 'error'
                continue
            numbers = [message_number(c) for c in row['CLs'] if message_number(c) is not None]
            if not numbers:
                rr.append(row)
                continue
            raw_fh = scope == 'error' and any(c.get('Var') == 'Error_Common_MessageActive' for c in row['CLs'])
            modified, branches = capture_messages(row, raw_fh)
            rr.append(modified)
            tests.append((scope, i, row, modified, raw_fh))
            for number, branch in branches:
                replacements.append({'scope': scope, 'row': i, 'number': number, 'extra_request_branch': branch})
                if scope == 'output':
                    source_coil = next(c['Var'] for c in row['CLs'] if c.get('__type') == 'ST')
                    match = re.fullmatch(r'(Output_(?:[AB]|Share)_Error_M)\[(\d+)\]', source_coil)
                    assert match, source_coil
                    e = ET.fromstring(h.fields(globals_before[match[1]]).get('EC', '<ECs/>'))
                    comment = next((x.get('C', '') for x in e if x.get('EK') == '[' + match[2] + ']'), '')
                    comments[number] = (comment or source_coil) + ' 異常表示'
                else:
                    comments[number] = {
                        101: 'ST1 搬送ワーク不一致', 102: 'ST2 搬送ワーク不一致', 103: 'ST3 搬送ワーク不一致',
                        104: 'ST4 搬送ワーク不一致', 105: 'ST5 搬送ワーク不一致', 106: 'ST6 搬送ワーク不一致',
                        107: 'ST7 搬送ワーク不一致', 108: 'A ST1 FH測定時間超過', 109: 'A ST1 FH異常',
                        110: 'A ST5 FH異常', 111: 'B ST1 FH異常', 112: 'B ST5 FH異常',
                        113: 'A ST1 FH判定OK', 114: 'A ST1 FH判定NG1', 115: 'A ST1 FH判定NG2',
                        116: 'A ST1 検査前ワーク不一致', 117: 'A ST5 FH測定時間超過',
                        118: 'A ST5 FH判定OK', 119: 'A ST5 FH判定NG1', 120: 'A ST5 FH判定NG2',
                        121: 'A ST5 検査前ワーク不一致',
                    }[number]
                    comments[number] = re.sub(r'^A ', 'A(左側) ', comments[number])
                    comments[number] = re.sub(r'^B ', 'B(右側) ', comments[number])
        new_ladders[name] = rr
        # 編集しない元の行は原文を維持。
        old_lines = texts[name].splitlines(keepends=True)
        rendered = []
        old_objects = {id(r): old_lines[i] for i, r in enumerate(ladders[name])}
        for row in rr:
            rendered.append(old_objects.get(id(row), h.dump_rows([row])))
        changes[name] = ''.join(rendered)
    assert sorted(r['number'] for r in replacements) == list(range(1, 122)), '要求番号の欠落/重複'
    # メッセージ番号を決定する唯一の場所。後段の代入が優先。
    move_template = next(c for rr in ladders.values() for r in rr for c in r['CLs'] if message_number(c) == 1)
    display_rows = []
    headers = {1: '#シリンダ異常\r\n前周期の表示要求（番号順・後段優先）',
               108: '#ST別異常\r\n当周期の表示要求（従来の優先順）',
               101: '#検査コンベア異常\r\nST別FH異常より優先',
               113: '#FH判定結果\r\n当周期の判定表示'}
    for number in PRIORITY:
        move = copy.deepcopy(move_template)
        next(p for p in move['In'] if p.get('Arg') == 'In')['Var'] = f'INT#{number}'
        cmt = (headers[number] + '\r\n' if number in headers else '') + comments[number]
        display_rows.append(h.dnf([[h.ld(request(number))]], [move], cmt))
    hmi_name = names['hmi']
    new_ladders[hmi_name] = display_rows + ladders[hmi_name]
    changes[hmi_name] = h.dump_rows(display_rows) + texts[hmi_name]
    # 既存の言語切替・表示文字は原文維持。未登録番号の文面を推測しない。
    assert new_ladders[hmi_name][-2:] == ladders[hmi_name]
    # 表示要求は通常コイルで各発生元が毎巡更新する。非保持BOOL配列。
    dtype = 'ARRAY[0..121] OF BOOL'
    added_global = h.decl(REQUEST, dtype, 'VAR_GLOBAL', '#HMI メッセージ表示要求', {0: '未使用', **comments})
    for scope in ('globals', 'mode_vars', 'other_vars', 'io_vars'):
        name = names[scope]
        line = added_global if scope == 'globals' else h.set_fields(added_global, G='VAR_EXTERNAL')
        changes[name] = h.add_decl(texts[name], line)
    # 優先判定をHMIへ移したため、旧補助BOOLは不要。
    mode_name = names['mode_vars']
    lines = changes[mode_name].splitlines(keepends=True)
    found = [l for l in lines if l.startswith('++D=') and h.fields(l)['N'] == 'Error_Common_MessageActive']
    assert len(found) == 1
    changes[mode_name] = ''.join(l for l in lines if l not in found)
    meta_name = names['metadata']
    meta = texts[meta_name]
    old_meta = {e.get('Name'): e for e in ET.fromstring(meta).iter('Variable')}
    element = copy.deepcopy(old_meta['Error_M'])
    for key, val in {'Name': REQUEST, 'Address': 'new_Controller_0.' + REQUEST, 'Id': str(h.uuid.uuid4()),
                     'DataTypeName': 'Boolean(121)', 'Comment': '#HMI メッセージ表示要求', 'IsConstant': 'false',
                     'IsReadOnly': 'false', 'Retained': 'false', 'InitialValue': ''}.items():
        element.set(key, val)
    element.tail = None
    marker = '  </VariableGroup>'
    assert marker in meta and REQUEST not in old_meta
    changes[meta_name] = meta.replace(marker, '    ' + ET.tostring(element, encoding='unicode') + '\r\r\n' + marker, 1)

    checks = verify(ladders, new_ladders, texts, changes, names, tests, display_rows)
    for name, text in changes.items():
        raw[name] = (b'\xef\xbb\xbf' if raw[name].startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
    with zipfile.ZipFile(STAGED, 'w') as z:
        z.comment = archive_comment
        for info in infos:
            z.writestr(info, raw[info.filename])
    with zipfile.ZipFile(STAGED) as z, zipfile.ZipFile(SOURCE) as before:
        assert z.testzip() is None and z.namelist() == before.namelist()
        for name in z.namelist():
            if name not in changes:
                assert z.read(name) == before.read(name), name
    report = {'source': str(SOURCE), 'staged': str(STAGED), 'destination': str(DEST),
              'source_sha256': source_hash, 'output_sha256': hashlib.sha256(STAGED.read_bytes()).hexdigest(),
              'names': names, 'changed_entries': list(changes), 'replacements': sorted(replacements, key=lambda r: r['number']),
              'priority': PRIORITY, 'message_comments': comments, 'checks': checks,
              'ladder_counts': {n: len(rr) for n, rr in new_ladders.items()},
              'new_declarations': [{'entry': names[s], 'name': REQUEST, 'type': dtype} for s in ('globals', 'mode_vars', 'other_vars', 'io_vars')],
              'native_validation': {}, 'native_variables': {}, 'full_application_build_verified': False,
              'hardware_transfer_performed': False}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'staged': str(STAGED), 'moves_centralized': len(replacements),
                      'rungs': sum(map(len, new_ladders.values())), 'checks': checks}, ensure_ascii=False, indent=2))


def verify(old, new, texts, changes, names, tests, display_rows):
    random_gen = random.Random(20261028)
    wiring_cases = 0
    # 元の表示MOVEだけを要求コイルへ置換。既存命令のパラメータ・パルスIdを照合。
    for scope, index, before, after, raw_fh in tests:
        original_other = [sig(c) for c in before['CLs'] if c['__type'] != 'HL' and message_number(c) is None
                          and c.get('Var') != 'Error_Common_MessageActive']
        edited_other = [sig(c) for c in after['CLs'] if c['__type'] != 'HL' and not c.get('Var', '').startswith(REQUEST)]
        assert original_other == edited_other, (scope, index, '元命令の変更')
        paired = []
        occurrences = collections.Counter()
        for c in before['CLs']:
            number = message_number(c)
            if number is not None:
                target = next(x for x in after['CLs'] if x.get('Var') == request(number))
                paired.append((c, target, number))
            elif c['__type'] in ('F', 'FB', 'ST'):
                signature = sig(c)
                matching = [x for x in after['CLs'] if sig(x) == signature]
                ordinal = occurrences[signature]
                assert ordinal < len(matching), (scope, index, signature)
                paired.append((c, matching[ordinal], '既存処理'))
                occurrences[signature] += 1
        keys = keys_for(before)
        # 配線検査では各Up・比較・TONの出力を独立に変化させる。
        vectors = itertools.product((False, True), repeat=len(keys)) if len(keys) <= 10 else (
            tuple(random_gen.getrandbits(1) != 0 for _ in keys) for _ in range(512))
        for vector in vectors:
            values = dict(zip(keys, vector))
            original_values = dict(values)
            if raw_fh:
                # 旧抑制の代わりにHMI内で搬送共通を後段に置くので、生入力側と比較。
                original_values['VAR:Error_Common_MessageActive'] = False
            p = semantic_power(before, original_values)
            q = semantic_power(after, values)
            for c, e, description in paired:
                assert ((c.get('X', 0), c.get('Y', 0)) in p) == ((e.get('X', 0), e.get('Y', 0)) in q), (scope, index, description, values)
            wiring_cases += 1
    # 121個すべて、発生元の通常コイル1個・HMI内MOVE1個。表示番号代入はHMIだけ。
    coils = collections.Counter()
    writers = []
    for name, rows in new.items():
        for row in rows:
            for c in row['CLs']:
                number = message_number(c)
                if number is not None:
                    assert name == names['hmi']
                    writers.append(number)
                if c['__type'] == 'ST' and c.get('Var', '').startswith(REQUEST):
                    assert not c.get('S') and not c.get('RS')
                    coils[c['Var']] += 1
    assert sorted(writers) == list(range(1, 122))
    assert coils == collections.Counter({request(i): 1 for i in range(1, 122)})
    assert all('Error_Common_MessageActive' not in changes.get(n, t) for n, t in texts.items()
               if n in new or t.startswith('[SLWD'))
    # 全元I/O・保持・型の属性、表示以外の回路が変わらないことを確認。
    at_count = 0
    for name, t in texts.items():
        if not t.startswith('[SLWD'):
            continue
        a, b = h.declarations(t), h.declarations(changes.get(name, t))
        assert len(b) == sum(l.startswith('++D=') for l in changes.get(name, t).splitlines())
        assert len(b) == len({n.lower() for n in b})
        for variable, line in a.items():
            if variable == 'Error_Common_MessageActive':
                assert variable not in b
            else:
                assert line == b[variable], (name, variable)
                at_count += bool(h.fields(line).get('AT'))
        for variable in b.keys() - a.keys():
            assert variable == REQUEST
            d = h.fields(b[variable])
            assert d['Const'] == d['RO'] == '0' and not d.get('AT') and d.get('R', '0') == '0'
    assert new[names['hmi']][-2:] == old[names['hmi']]
    changed_ladders = {names[k] for k in ('error', 'output', 'fh', 'hmi')}
    assert all(rr == new[n] for n, rr in old.items() if n not in changed_ladders)
    assert names['task'] not in changes
    # HMI直前の元の優先：前巡IO → 当巡モード/FHエラー → 当巡FH判定。
    # 新規HMIが、前巡IO要求と当巡要求の混在をこの順で消費することを確認。
    priority_cases = 0
    def old_result(previous, io_events, current):
        value = previous
        for n in range(1, 101):
            if n in io_events:
                value = n
        common = any(n in current for n in range(101, 108))
        for n in range(101, 108):
            if n in current:
                value = n
        if not common:
            for n in (108, 109, 116, 117, 110, 121, 111, 112):
                if n in current:
                    value = n
        for n in (113, 114, 115, 118, 119, 120):
            if n in current:
                value = n
        return value
    def new_result(previous, io_events, current):
        value = previous
        for row, n in zip(display_rows, PRIORITY):
            # HMI実回路の入力要求を確認。
            assert row['CLs'][0]['Var'] == request(n)
            if n in (io_events if n <= 100 else current):
                value = n
        return value
    # 全単独・全組合せペア + ランダム同時発生。ゼロ件時は旧番号を保持。
    for a in range(122):
        for b in range(a, 122):
            events = {i for i in (a, b) if i}
            io_events = {i for i in events if i <= 100}
            current = events - io_events
            for previous in (0, 77):
                assert old_result(previous, io_events, current) == new_result(previous, io_events, current)
                priority_cases += 1
    for _ in range(4096):
        events = {i for i in range(1, 122) if random_gen.randrange(5) == 0}
        io_events = {i for i in events if i <= 100}; current = events - io_events
        assert old_result(9, io_events, current) == new_result(9, io_events, current)
        priority_cases += 1
    # 一巡だけのIOパルスが次のHMIまで保持され、翌巡以降は重複発生しない。
    pulse_cases = 0
    for io_number in range(1, 101):
        pending = set(); current_old = 0; current_new = 0
        for scan in range(5):
            before_output = old_result(current_old, pending, set())
            current_new = new_result(current_new, pending, set())
            assert before_output == current_new
            pending = {io_number} if scan == 1 else set()
            current_old = io_number if pending else before_output
            pulse_cases += 1
    return {'source_wiring_cases': wiring_cases, 'hmi_priority_cases': priority_cases, 'single_scan_io_pulse_cases': pulse_cases,
            'all_messages_centralized': 121, 'source_request_normal_coils': len(coils), 'io_assignment_count': at_count,
            'unchanged_ladder_sections': len(old) - 4, 'task_and_section_order_unchanged': True,
            'existing_hmi_language_text_unchanged': True, 'all_existing_Up_ids_preserved': True,
            'stop_and_work_data_instructions_preserved': True}


def publish():
    report = json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert report['native_validation'] and report['native_variables']
    assert all('PARSE_FAIL=0 MODEL_FAIL=0' in s for s in report['native_validation'].values())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest() == report['output_sha256']
    with STAGED.open('rb') as src, DEST.open('xb') as target:
        shutil.copyfileobj(src, target)
    assert hashlib.sha256(DEST.read_bytes()).hexdigest() == report['output_sha256']
    print('保存完了：' + str(DEST))


if __name__ == '__main__':
    publish() if '--publish' in sys.argv else build()
