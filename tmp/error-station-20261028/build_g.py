"""指定E版の異常をST・原因別に整理する。実機接続・転送は行わない。"""
from pathlib import Path
import collections
import copy
import hashlib
import itertools
import json
import re
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
BASE = Path(__file__).resolve().parent
J = json.loads((BASE / 'inspection.json').read_text(encoding='utf-8'))
SOURCE = Path(J['source'])
DEST = SOURCE.with_name(SOURCE.name.replace('20261029E', '20261029G'))
STAGED = BASE / DEST.name
REPORT = BASE / 'verification.json'
NAMES = J['names']
TEXTS = J['texts']
ROWS = J['ladders']
LABELS = {
    'ST1_A': 'A(左側) ST1 カメラ1', 'ST1_B': 'B(右側) ST1 カメラ1',
    'ST2_A': 'A(左側) ST2 高さ検査', 'ST3_A': 'A(左側) ST3 NG1排出',
    'ST4_A': 'A(左側) ST4 反転1', 'ST5_A': 'A(左側) ST5 カメラ2',
    'ST5_B': 'B(右側) ST5 カメラ2', 'ST6_A': 'A(左側) ST6 反転2',
    'ST7_A': 'A(左側) ST7 SF排出',
}
ACTIVE = {'ST1_A': [1, 2, 3], 'ST1_B': [1], 'ST2_A': [3], 'ST3_A': [1, 3],
          'ST4_A': [3], 'ST5_A': [1, 2, 3], 'ST5_B': [1], 'ST6_A': [3], 'ST7_A': [3, 4]}
CAUSES = {0: '総合異常', 1: '機器異常', 2: 'タイムアウト', 3: 'ワーク不一致', 4: '満杯'}
MAPPING = {3: ('ST1_A', 0), 5: ('ST3_A', 1), 6: ('ST2_A', 0), 7: ('ST3_A', 3),
           8: ('ST4_A', 0), 9: ('ST5_A', 0), 10: ('ST1_B', 0), 11: ('ST5_B', 0),
           12: ('ST6_A', 0), 13: ('ST7_A', 0)}


def bit(st, i):
    return f'Error_{st}_M[{i}]'


def walk(v):
    if isinstance(v, dict):
        yield v
        for x in v.values():
            yield from walk(x)
    elif isinstance(v, list):
        for x in v:
            yield from walk(x)


def fields(line):
    return dict(x.split('=', 1) for x in line[2:].split('\t') if '=' in x)


def set_fields(line, **kwargs):
    for key, value in kwargs.items():
        p = re.compile(r'(?<=\t)' + re.escape(key) + r'=[^\t\r\n]*')
        line = p.sub(lambda m: key + '=' + value, line) if p.search(line) else line + '\t' + key + '=' + value
    return line


def ec_xml(values):
    return '<ECs>' + ''.join('<EC EK="[%s]" C="%s" />' % (i, escape(c, {'"': '&quot;'})) for i, c in sorted(values.items())) + '</ECs>'


def decl(name, dtype, group, comment, ec=None):
    line = f'++D={dtype}\tN={name}\tG={group}\tCom={comment}\tConst=0\tRO=0'
    return line + ('\tEC=' + ec_xml(ec) if ec else '')


def declarations(text):
    return {fields(l)['N']: l for l in text.splitlines() if l.startswith('++D=')}


def add_decl(text, line, local=False):
    assert fields(line)['N'] not in declarations(text)
    if local:
        marker = '+GN=VAR_EXTERNAL'
        assert marker in text
        return text.replace(marker, line + '\r\n' + marker, 1)
    return text.rstrip('\r\n') + '\r\n' + line + '\r\n'


def normalize(row):
    row.setdefault('VLs', [])
    ix = 0
    for c in row['CLs']:
        for node in walk(c):
            if node.get('__type') in ('LD', 'ST', 'F', 'FB', 'PRM'):
                node['Ix'] = ix
                ix += 1
            if 'Id' in node:
                node['Id'] = str(uuid.uuid4())
    row['LRI'], row['RRI'] = ix, ix + 1
    ids = {}
    for v in row.get('VLs', []):
        ids.setdefault(v['Ix'], ix + 2 + len(ids))
        v['Ix'] = ids[v['Ix']]
    coords = [(c.get('X', 0), c.get('Y', 0)) for c in row['CLs']]
    assert len(coords) == len(set(coords))
    return row


def ld(name, neg=False):
    c = {'__type': 'LD', 'Var': name}
    if neg:
        c['Not'] = True
    return c


def st(name, setting=False, reset=False):
    c = {'__type': 'ST', 'Var': name}
    if setting:
        c['S'] = True
    if reset:
        c['RS'] = True
    return c


def dnf(branches, outputs, cmt, guards=()):
    """並列条件→共通直列条件→出力。出力分岐が左レールへ直結しないよう検査する。"""
    width = max(map(len, branches))
    cells = []
    wires = []
    for y, branch in enumerate(branches):
        for x in range(width):
            c = copy.deepcopy(branch[x]) if x < len(branch) else {'__type': 'HL'}
            c.update(X=x, Y=y)
            cells.append(c)
    wires += [{'Ix': 0, 'X': width, 'Y': y} for y in range(len(branches) - 1)]
    for offset, c in enumerate(guards):
        c = copy.deepcopy(c)
        c.update(X=width + offset, Y=0)
        cells.append(c)
    out_x = width + len(guards)
    for y, c in enumerate(outputs):
        c = copy.deepcopy(c)
        c.update(X=out_x, Y=y)
        cells.append(c)
    wires += [{'Ix': 1, 'X': out_x, 'Y': y} for y in range(len(outputs) - 1)]
    return normalize({'CLs': cells, 'VLs': wires, 'CMT': cmt})


def latch(station, cause, triggers):
    target = bit(station, cause)
    return dnf(triggers + [[ld(target)]], [st(target)], CAUSES[cause] + '（RESETで解除）', [ld('In_Sw_RESET', True)])


def overall(station):
    return dnf([[ld(bit(station, i))] for i in ACTIVE[station]], [st(bit(station, 0))], '総合異常')


def pause(signal, number):
    return dnf([[ld(signal)]], [st(f'Pause[{number}]', setting=True), st('Out_TDC_Stop', setting=True)], f'一時停止保持：Pause[{number}]')


def dump_rows(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\r\n' for r in rows)


def replace_old(text):
    def sub(m):
        station, cause = MAPPING[int(m[1])]
        return bit(station, cause)
    return re.sub(r'\bError_M\[(3|[5-9]|1[0-3])\]', sub, text)


def power(row, values):
    """ブール回路の限定検査。タイマーQ・比較結果は別途与える。"""
    graph = collections.defaultdict(list)
    max_y = max([c.get('Y', 0) for c in row['CLs']] + [w.get('Y', 0) + 1 for w in row.get('VLs', [])])
    for c in row['CLs']:
        x, y = c.get('X', 0), c.get('Y', 0)
        condition = True
        if c['__type'] in ('LD', 'FB'):
            condition = values.get(c.get('Var'), False)
            condition = not condition if c.get('Not') else condition
        elif c['__type'] == 'F' and c.get('Name') == '=':
            args = [a.get('Var') for a in c['In'] if a.get('__type') == 'PRM']
            def val(a):
                return a == 'TRUE' if a in ('TRUE', 'FALSE') else values.get(a, False)
            condition = val(args[0]) == val(args[1])
        elif c['__type'] == 'F' and c.get('Name') == 'Up':
            condition = values.get('Up', False)
        if condition:
            graph[(x, y)].append((x + 1, y))
    for w in row.get('VLs', []):
        a = (w.get('X', 0), w.get('Y', 0))
        b = (a[0], a[1] + 1)
        graph[a].append(b)
        graph[b].append(a)
    reached = {(0, y) for y in range(max_y + 1)}
    todo = list(reached)
    while todo:
        for b in graph[todo.pop()]:
            if b not in reached:
                reached.add(b)
                todo.append(b)
    return reached


def apply_coils(row, values):
    reached = power(row, values)
    for c in row['CLs']:
        if c['__type'] != 'ST':
            continue
        on = (c.get('X', 0), c.get('Y', 0)) in reached
        if c.get('S'):
            values[c['Var']] = values.get(c['Var'], False) or on
        elif c.get('RS'):
            values[c['Var']] = values.get(c['Var'], False) and not on
        else:
            values[c['Var']] = on


def build():
    assert SOURCE.name.endswith('20261029E.smc2') and not DEST.exists()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == J['sha256']
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        raw = {n: z.read(n) for n in z.namelist()}
        infos, archive_comment = z.infolist(), z.comment
    errors = ROWS[NAMES['error']]
    assert len(errors) == 24
    changes = {}
    # 共通回路の順序・内容を保持。搬送共通はST群の前に置く。
    new_errors = copy.deepcopy(errors[:11]) + [copy.deepcopy(errors[16])]
    common_message = dnf([[ld(f'Ins_A_Cv_M[{i}]')] for i in (6, 8, 10, 12, 14, 16, 18)],
                         [st('Error_Common_MessageActive')], '#共通表示の優先判定', [ld('Error_M[4]')])
    new_errors.append(common_message)
    # ST0は専用監視がないため、架空のエラー回路を作らない。
    station_blocks = {}
    station_latches = {}
    device_inputs = {'ST1_A': 'FH_Line0_Error_Status_1', 'ST1_B': 'FH_Line2_Error_Status_1',
                     'ST5_A': 'FH_Line1_Error_Status_1', 'ST5_B': 'FH_Line3_Error_Status_1'}
    mismatch_inputs = {'ST1_A': 'ST1_A_Ca1_M[6]', 'ST2_A': 'ST2_A_Hgt_M[8]',
                       'ST3_A': 'ST3_A_Dis1_M[11]', 'ST4_A': 'ST4_A_Rev1_M[10]',
                       'ST5_A': 'ST5_A_Ca2_M[6]', 'ST6_A': 'ST6_A_Rev2_M[10]'}
    pauses = {'ST1_A': 3, 'ST1_B': 10, 'ST2_A': 6, 'ST4_A': 8,
              'ST5_A': 9, 'ST5_B': 11, 'ST6_A': 12, 'ST7_A': 13}
    for station in LABELS:
        block = []
        if station in ('ST1_A', 'ST5_A'):
            source = errors[11 if station == 'ST1_A' else 12]
            cells = copy.deepcopy(source['CLs'][:2])
            cells.append(dict(st(f'Error_{station}_Timeout'), X=2))
            block.append(normalize({'CLs': cells, 'CMT': 'FH測定監視：10秒'}))
        latches = []
        for cause in ACTIVE[station]:
            if cause == 1 and station in device_inputs:
                triggers = [[ld(device_inputs[station])]]
            elif cause == 1 and station == 'ST3_A':
                triggers = [[ld(v)] for v in ('RCON1_1_IN_Alarm', 'RCON1_1_IN_EmergencyStop', 'M9999')]
            elif cause == 2:
                triggers = [[ld(f'Error_{station}_Timeout')]]
            elif cause == 3 and station in mismatch_inputs:
                triggers = [[ld(mismatch_inputs[station])]]
            elif station == 'ST7_A':
                triggers = [[ld('ST7_A_Dis2_M[11]'), ld(f'Error_ST7_A_Source_M[{cause}]')]]
            else:
                raise AssertionError((station, cause))
            r = latch(station, cause, triggers)
            latches.append(r)
            block.append(r)
        block.append(overall(station))
        if station == 'ST3_A':
            block += [pause(bit(station, 1), 5), pause(bit(station, 3), 7)]
        else:
            block.append(pause(bit(station, 0), pauses[station]))
        block[0]['CMT'] = '#' + LABELS[station] + '\r\n' + block[0]['CMT']
        station_blocks[station] = block
        station_latches[station] = latches
        new_errors += block
    # FHクリア回路は原形維持。タイマー/Upを複製しない。
    new_errors.append(copy.deepcopy(errors[15]))
    # 表示は元の優先順に集約。搬送共通の既存表示を上書きしない。
    display_specs = [('Error_ST1_A_Timeout', 108), (device_inputs['ST1_A'], 109),
                     (mismatch_inputs['ST1_A'], 116), ('Error_ST5_A_Timeout', 117),
                     (device_inputs['ST5_A'], 110), (mismatch_inputs['ST5_A'], 121),
                     (device_inputs['ST1_B'], 111), (device_inputs['ST5_B'], 112)]
    move_template = next(c for c in errors[11]['CLs'] if c.get('Name') == 'MOVE')
    display_rows = []
    for i, (trigger, number) in enumerate(display_specs):
        move = copy.deepcopy(move_template)
        next(p for p in move['In'] if p.get('Arg') == 'In')['Var'] = f'INT#{number}'
        r = dnf([[ld(trigger), ld('Error_Common_MessageActive', True)]], [move],
                ('#エラーメッセージ選択\r\n' if i == 0 else '') + f'表示番号：{number}')
        display_rows.append(r)
    new_errors += display_rows
    restart = copy.deepcopy(errors[23])
    for node in walk(restart):
        if 'Var' in node:
            node['Var'] = replace_old(node['Var'])
    restart['CMT'] = '#自動運転再開\r\n既存の開始・安全・異常・Pause解除条件を維持'
    new_errors.append(restart)
    # 原本の共通行はJSONオブジェクトだけでなく元の行バイト表現も維持する。
    original_lines = TEXTS[NAMES['error']].splitlines(keepends=True)
    serial = dump_rows(new_errors).splitlines(keepends=True)
    serial[:11] = original_lines[:11]
    serial[11] = original_lines[16]
    serial[len(new_errors) - len(display_rows) - 2] = original_lines[15]
    changes[NAMES['error']] = ''.join(serial)

    # ST7の元SET信号と同じ監視条件で、発生理由だけを記録する。
    # アクチュエータ・監視対象・元のUp・元のST7全行は変更しない。
    clear_source = dnf([[ld('ST7_A_Dis2_M[11]', True)]],
                       [st('Error_ST7_A_Source_M[3]', reset=True), st('Error_ST7_A_Source_M[4]', reset=True)],
                       '#A(左側) ST7 異常理由\r\n元の異常が解除されたら理由を消去')
    source_mismatch = dnf([
        [ld('ST7_A_Dis2_M[8]'), ld('TimerQ_In_Sen_Work_A_Pos_07', True), ld('Station_A_Data[7].Work_On')],
        [ld('ST7_A_Dis2_M[8]'), ld('TimerQ_In_Sen_Work_A_Pos_07'), ld('Station_A_Data[7].Work_On', True)],
    ], [st('Error_ST7_A_Source_M[3]', setting=True)], 'ワーク不一致の発生理由を保持')
    source_full = dnf([[ld('ST7_A_Dis2_M[8]'), ld('TimerQ_In_Sen_NG2_Tray_B_Full')]],
                      [st('Error_ST7_A_Source_M[4]', setting=True)], '満杯の発生理由を保持（既存B側入力）')
    st7_lines = TEXTS[NAMES['st7']].splitlines(keepends=True)
    changes[NAMES['st7']] = ''.join(st7_lines[:8]) + dump_rows([clear_source]) + st7_lines[8] + dump_rows([source_mismatch, source_full]) + ''.join(st7_lines[9:])

    # 他セクションの派生参照も検索。現版では再開回路以外の旧ST異常参照はない。
    external_replacements = []
    for name, rows in ROWS.items():
        if name == NAMES['error']:
            continue
        t = changes.get(name, TEXTS[name])
        replaced = replace_old(t)
        if replaced != t:
            changes[name] = replaced
            external_replacements.append(name)
    assert not external_replacements

    # グローバル/外部変数の原因番号を共通化。未実装の監視は予備と明記。
    global_lines = {}
    for station, label in LABELS.items():
        comments = {i: CAUSES[i] if i == 0 or i in ACTIVE[station] else '予備（監視なし）' for i in range(5)}
        global_lines[f'Error_{station}_M'] = decl(f'Error_{station}_M', 'ARRAY[0..4] OF BOOL', 'VAR_GLOBAL', '#' + label + ' 異常', comments)
    global_lines['Error_ST7_A_Source_M'] = decl('Error_ST7_A_Source_M', 'ARRAY[0..4] OF BOOL', 'VAR_GLOBAL',
                                              '#A(左側) ST7 発生理由（内部保持）', {3: 'ワーク不一致', 4: '満杯（既存B側入力）'})
    for name, text in TEXTS.items():
        if not text.startswith('[SLWD'):
            continue
        lines = text.splitlines(keepends=True)
        changed = False
        for i, line in enumerate(lines):
            if not line.startswith('++D=') or fields(line)['N'] != 'Error_M':
                continue
            p = fields(line)
            ec = ET.fromstring(p.get('EC', '<ECs/>'))
            comments = {int(e.get('EK').strip('[]')): e.get('C', '') for e in ec}
            for old, (station, cause) in MAPPING.items():
                if old in comments:
                    comments[old] = f'未使用：{bit(station, cause)}へ移行'
            ending = '\r\n' if line.endswith('\r\n') else '\n'
            lines[i] = set_fields(line.rstrip('\r\n'), EC=ec_xml(comments)) + ending
            changed = True
        if changed:
            changes[name] = ''.join(lines)
    for line in global_lines.values():
        changes[NAMES['globals']] = add_decl(changes.get(NAMES['globals'], TEXTS[NAMES['globals']]), line)
        p = fields(line)
        for scope in ('mode_vars', 'movement_vars') if p['N'] == 'Error_ST7_A_Source_M' else ('mode_vars',):
            name = NAMES[scope]
            changes[name] = add_decl(changes.get(name, TEXTS[name]), set_fields(line, G='VAR_EXTERNAL'))
    for local in ('Error_ST1_A_Timeout', 'Error_ST5_A_Timeout', 'Error_Common_MessageActive'):
        comment = '搬送共通メッセージ優先' if local == 'Error_Common_MessageActive' else 'FHタイムアウト（非保持）'
        changes[NAMES['mode_vars']] = add_decl(changes[NAMES['mode_vars']], decl(local, 'BOOL', 'VAR', comment), local=True)

    # HMI向け型情報。元の変数メタ情報を変更せず、新しいグローバル10個だけを追加。
    meta = TEXTS[NAMES['metadata']]
    old_meta = {e.get('Name'): e for e in ET.fromstring(meta).iter('Variable')}
    added = []
    for name, line in global_lines.items():
        assert name not in old_meta
        el = copy.deepcopy(old_meta['Error_M'])
        for key, value in {'Name': name, 'Address': 'new_Controller_0.' + name, 'Id': str(uuid.uuid4()),
                           'DataTypeName': 'Boolean(4)', 'Comment': fields(line)['Com'], 'IsConstant': 'false',
                           'IsReadOnly': 'false', 'Retained': 'false', 'InitialValue': ''}.items():
            el.set(key, value)
        el.tail = None
        added.append(ET.tostring(el, encoding='unicode'))
    marker = '  </VariableGroup>'
    assert marker in meta
    changes[NAMES['metadata']] = meta.replace(marker, ''.join('    ' + e + '\r\r\n' for e in added) + marker, 1)
    ET.fromstring(changes[NAMES['metadata']])

    # 宣言・配線・ラッチ・表示・ST7原因保持を検査する。
    new_ladders = dict(ROWS)
    for name in ROWS:
        if name in changes:
            new_ladders[name] = [json.loads(l) for l in changes[name].splitlines() if l.strip()]
    check = verify(new_ladders, changes, station_blocks, station_latches, display_rows,
                   clear_source, source_mismatch, source_full, common_message)
    for name, text in changes.items():
        if not text.startswith('[SLWD'):
            continue
        old_decls, new_decls = declarations(TEXTS[name]), declarations(text)
        assert len(new_decls) == sum(l.startswith('++D=') for l in text.splitlines())
        assert len(new_decls) == len({n.lower() for n in new_decls})
        for variable, before in old_decls.items():
            a, b = fields(before), fields(new_decls[variable])
            a.pop('EC', None); b.pop('EC', None)
            assert a == b, (name, variable)
        for variable in set(new_decls) - set(old_decls):
            p = fields(new_decls[variable])
            assert p['Const'] == '0' and p['RO'] == '0' and 'AT' not in p
    # 全既存I/O割付・型/構造体・出力回路・他エントリは不変。
    assert all(k in TEXTS for k in changes)
    expected_changed_ladders = {NAMES['error'], NAMES['st7']}
    assert {n for n in changes if n in ROWS} == expected_changed_ladders
    for name, text in TEXTS.items():
        if name in ROWS or text.startswith('[SLWD') or name == NAMES['metadata']:
            continue
        assert name not in changes
    for name, text in changes.items():
        raw[name] = (b'\xef\xbb\xbf' if raw[name].startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
    with zipfile.ZipFile(STAGED, 'w') as z:
        z.comment = archive_comment
        for info in infos:
            z.writestr(info, raw[info.filename])
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist() == [i.filename for i in infos]
        with zipfile.ZipFile(SOURCE) as src:
            for name in z.namelist():
                if name not in changes:
                    assert z.read(name) == src.read(name)
    report = {'source': str(SOURCE), 'staged': str(STAGED), 'destination': str(DEST),
              'source_sha256': J['sha256'], 'output_sha256': hashlib.sha256(STAGED.read_bytes()).hexdigest(),
              'changed_entries': list(changes), 'new_globals': list(global_lines),
              'new_declarations': [{'entry': name, 'name': variable, 'type': fields(line)['D']}
                                   for name, text in changes.items() if text.startswith('[SLWD')
                                   for variable, line in declarations(text).items() if variable not in declarations(TEXTS[name])],
              'ladder_counts': {n: len(r) for n, r in new_ladders.items()},
              'checks': check, 'native_validation': {}, 'native_variables': {},
              'full_application_build_verified': False, 'hardware_transfer_performed': False}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'staged': str(STAGED), 'changed_entries': len(changes), 'new_globals': len(global_lines),
                      'rungs': sum(map(len, new_ladders.values())), 'checks': check}, ensure_ascii=False, indent=2))


def verify(new_ladders, changes, blocks, latches, displays, clear, mismatch, full, common):
    errors = new_ladders[NAMES['error']]
    original = ROWS[NAMES['error']]
    assert errors[:11] == original[:11] and errors[11] == original[16]
    assert original[15] in errors
    for name, rr in new_ladders.items():
        for r in rr:
            for node in walk(r):
                assert not re.fullmatch(r'Error_M\[(?:3|[5-9]|1[0-3])\]', node.get('Var', ''))
    original_st7 = ROWS[NAMES['st7']]
    edited_st7 = new_ladders[NAMES['st7']]
    assert edited_st7[:8] == original_st7[:8]
    assert edited_st7[9] == original_st7[8] and edited_st7[12:] == original_st7[9:]
    # 既存Pauseへの書込みは元と同じ番号・S/RS、共通回路も不変。
    def pause_writes(rr):
        return collections.Counter((c['Var'], bool(c.get('S')), bool(c.get('RS'))) for r in rr for c in r['CLs']
                                   if c.get('__type') == 'ST' and c.get('Var', '').startswith('Pause['))
    assert pause_writes(errors) == pause_writes(original)
    assert next(r for r in errors if r.get('CMT', '').startswith('#自動運転再開'))['CLs'] == [
        {**c, **({'Var': replace_old(c['Var'])} if 'Var' in c else {})} for c in original[23]['CLs']]
    # 原因ラッチと総合の全状態組合せ。元ラッチとORの等価性。
    latch_cases = 0
    for station, active in ACTIVE.items():
        for history in itertools.product((False, True), repeat=len(active)):
            for triggers in itertools.product((False, True), repeat=len(active)):
                for reset in (False, True):
                    after = [(h or t) and not reset for h, t in zip(history, triggers)]
                    assert any(after) == ((any(history) or any(triggers)) and not reset)
                    v = {bit(station, i): x for i, x in zip(active, after)}
                    apply_coils(overall(station), v)
                    assert v[bit(station, 0)] == any(after)
                    latch_cases += 1
    # 新規ラッチの実際の配線を、接点全組合せで独立評価。
    wiring_cases = 0
    for station, rr in latches.items():
        for cause, row in zip(ACTIVE[station], rr):
            keys = sorted({c['Var'] for c in row['CLs'] if c['__type'] == 'LD'})
            for vals in itertools.product((False, True), repeat=len(keys)):
                v = dict(zip(keys, vals)); before = dict(v)
                apply_coils(row, v)
                guard_x = next(c['X'] for c in row['CLs'] if c.get('Var') == 'In_Sw_RESET')
                branches = []
                for y in sorted({c.get('Y', 0) for c in row['CLs'] if c.get('X', 0) < guard_x}):
                    branches.append(all(before[c['Var']] != c.get('Not', False) for c in row['CLs']
                                        if c.get('Y', 0) == y and c.get('X', 0) < guard_x and c['__type'] == 'LD'))
                assert v[bit(station, cause)] == (any(branches) and not before['In_Sw_RESET'])
                wiring_cases += 1
    # 表示優先順：元のFH→搬送共通と、新しい共通→FH抑制が同じになる。
    message_numbers = (108, 109, 116, 117, 110, 121, 111, 112)
    message_cases = 0
    for values in itertools.product((False, True), repeat=8):
        for common_active, reset in itertools.product((False, True), repeat=2):
            old = 999
            for on, no in zip(values, message_numbers):
                if on:
                    old = no
            if common_active:
                old = 101
            new = 101 if common_active else 999
            for row, on, no in zip(displays, values, message_numbers):
                trigger = row['CLs'][0]['Var']
                v = {trigger: on, 'Error_Common_MessageActive': common_active, 'In_Sw_RESET': reset}
                move = next(c for c in row['CLs'] if c['__type'] == 'F')
                if (move['X'], move['Y']) in power(row, v):
                    new = no
            assert old == new
            message_cases += 1
    # 搬送共通の表示抑制フラグが元MOVE分岐の通電条件に一致する。
    common_cases = 0
    for old_hold, reset, ins_values in itertools.product((False, True), (False, True), itertools.product((False, True), repeat=7)):
        v = {'Error_M[4]': old_hold, 'In_Sw_RESET': reset}
        v.update({f'Ins_A_Cv_M[{i}]': x for i, x in zip((6, 8, 10, 12, 14, 16, 18), ins_values)})
        apply_coils(original[16], v)
        original_power = power(original[16], {**v, 'Error_M[4]': old_hold})
        original_display = any((c.get('X', 0), c.get('Y', 0)) in original_power for c in original[16]['CLs']
                               if c.get('Name') == 'MOVE' and any(p.get('Var') == 'HMI_MessageNo[0]' for p in c.get('Out', [])))
        apply_coils(common, v)
        assert v['Error_Common_MessageActive'] == original_display
        common_cases += 1
    # ST7の元SETと理由フラグの同値性を全監視入力・保持・リセットで検証。
    st7_cases = 0
    for old_source, old3, old4 in ((False, False, False), (False, True, False), (False, False, True),
                                   (True, True, False), (True, False, True), (True, True, True)):
        for gate, sensor, work, tray in itertools.product((False, True), repeat=4):
            v = {'ST7_A_Dis2_M[11]': old_source, 'Error_ST7_A_Source_M[3]': old3,
                 'Error_ST7_A_Source_M[4]': old4, 'ST7_A_Dis2_M[8]': gate,
                 'TimerQ_In_Sen_Work_A_Pos_07': sensor, 'Station_A_Data[7].Work_On': work,
                 'TimerQ_In_Sen_NG2_Tray_B_Full': tray}
            apply_coils(clear, v)
            new_source = old_source or (gate and (sensor != work or tray))
            v['ST7_A_Dis2_M[11]'] = new_source
            apply_coils(mismatch, v); apply_coils(full, v)
            assert new_source == (v['Error_ST7_A_Source_M[3]'] or v['Error_ST7_A_Source_M[4]'])
            for prior3, prior4, reset in itertools.product((False, True), repeat=3):
                vv = {**v, bit('ST7_A', 3): prior3, bit('ST7_A', 4): prior4, 'In_Sw_RESET': reset}
                for r in latches['ST7_A']:
                    apply_coils(r, vv)
                apply_coils(overall('ST7_A'), vv)
                assert vv[bit('ST7_A', 0)] == ((new_source or prior3 or prior4) and not reset)
                st7_cases += 1
    # ST3の2種類のPauseを独立維持。
    pause_cases = 0
    for device, mismatch_on in itertools.product((False, True), repeat=2):
        v = {bit('ST3_A', 1): device, bit('ST3_A', 3): mismatch_on}
        for r in blocks['ST3_A'][-2:]:
            apply_coils(r, v)
        assert v['Pause[5]'] == device and v['Pause[7]'] == mismatch_on
        pause_cases += 1
    return {'common_source_rungs_preserved': 13, 'source_st7_rungs_preserved': len(original_st7),
            'latch_equivalence_cases': latch_cases, 'latch_wiring_cases': wiring_cases,
            'hmi_priority_cases': message_cases, 'common_hmi_enable_cases': common_cases,
            'st7_attribution_cases': st7_cases, 'st3_pause_cases': pause_cases,
            'physical_io_assignments_unchanged': True, 'all_other_sections_unchanged': True}


def publish():
    r = json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert r['native_validation'] and r['native_variables']
    assert all('PARSE_FAIL=0 MODEL_FAIL=0' in s for s in r['native_validation'].values())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == r['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest() == r['output_sha256']
    with STAGED.open('rb') as src, DEST.open('xb') as target:
        shutil.copyfileobj(src, target)
    assert hashlib.sha256(DEST.read_bytes()).hexdigest() == r['output_sha256']
    print('保存完了：' + str(DEST))


if __name__ == '__main__':
    publish() if '--publish' in sys.argv else build()
