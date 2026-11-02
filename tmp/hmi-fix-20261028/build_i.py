"""FHの分断4行を原回路形状へ戻し、表示要求をHMI消費後に解除する。"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import itertools
import json
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hmi_builder', BASE.parent / 'hmi-central-20261028/build_h.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
PREV = json.loads(b.REPORT.read_text(encoding='utf-8-sig'))
SOURCE = Path(PREV['destination'])
DEST = SOURCE.with_name(SOURCE.name.replace('20261029H', '20261029I'))
STAGED = BASE / DEST.name
REPORT = BASE / 'verification.json'
NUMBERS = (113, 114, 115, 118, 119, 120)


def build():
    assert not DEST.exists(), '既存I版を上書きしません'
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PREV['output_sha256'], 'H版が更新されています'
    assert hashlib.sha256(Path(PREV['source']).read_bytes()).hexdigest() == PREV['source_sha256']
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        raw = {n: z.read(n) for n in z.namelist()}
        infos, archive_comment = z.infolist(), z.comment
    with zipfile.ZipFile(PREV['source']) as z:
        good_fh = [json.loads(l) for l in z.read(PREV['names']['fh']).decode('utf-8-sig').splitlines() if l.strip()]
    fh_name, hmi_name = PREV['names']['fh'], PREV['names']['hmi']
    fh_text = raw[fh_name].decode('utf-8-sig')
    fh_lines = fh_text.splitlines(keepends=True)
    fixes = []
    changed_fh = [json.loads(l) for l in fh_lines if l.strip()]
    for index in (5, 6, 13, 14):
        row = copy.deepcopy(good_fh[index])
        numbers = []
        for c in row['CLs']:
            number = b.message_number(c)
            if number is None:
                continue
            assert number in NUMBERS
            next(p for p in c['In'] if p.get('Arg') == 'In')['Var'] = 'TRUE'
            next(p for p in c['Out'] if p.get('Arg') == 'Out')['Var'] = b.request(number)
            numbers.append(number)
        assert numbers
        # 接点/命令の配置・配線・Ix/Up Idを元の正常回路と完全一致させ、MOVEの引数だけ変更。
        restored = copy.deepcopy(row)
        for c in restored['CLs']:
            outs = [p for p in c.get('Out', []) if p.get('Arg') == 'Out' and p.get('Var', '').startswith(b.REQUEST)]
            if outs:
                number = int(outs[0]['Var'].split('[')[1].rstrip(']'))
                outs[0]['Var'] = 'HMI_MessageNo[0]'
                next(p for p in c['In'] if p.get('Arg') == 'In')['Var'] = f'INT#{number}'
        assert restored == good_fh[index]
        changed_fh[index] = row
        fh_lines[index] = b.h.dump_rows([row])
        fixes.append({'row': index, 'requests': numbers, 'original_geometry_preserved': True})
    changes = {fh_name: ''.join(fh_lines)}
    hmi_text = raw[hmi_name].decode('utf-8-sig')
    hmi_rows = [json.loads(l) for l in hmi_text.splitlines() if l.strip()]
    assert len(hmi_rows) == 123
    # FHのTRUE要求は表示選択の後で解除。停止回路や表示番号はリセットしない。
    reset_row = b.h.dnf([[b.h.ld('P_On')]], [b.h.st(b.request(n), reset=True) for n in NUMBERS],
                        '#FH表示要求の消費\r\n番号選択後に解除（単発要求を残さない）')
    lines = hmi_text.splitlines(keepends=True)
    # 原文に空行があるので、先頭121行（生成した表示選択行）の境界を使う。
    assert all(json.loads(lines[i]).get('CLs') for i in range(121))
    changes[hmi_name] = ''.join(lines[:121]) + b.h.dump_rows([reset_row]) + ''.join(lines[121:])
    after_hmi = hmi_rows[:121] + [reset_row] + hmi_rows[121:]
    assert after_hmi[-2:] == hmi_rows[-2:]

    # 元の命令形状と接続を保った4行の通電を元G回路と照合。
    wiring_cases = 0
    for fix in fixes:
        old, new = good_fh[fix['row']], changed_fh[fix['row']]
        keys = b.keys_for(old)
        for bits in itertools.product((False, True), repeat=len(keys)):
            values = dict(zip(keys, bits))
            assert b.semantic_power(old, values) == b.semantic_power(new, values)
            wiring_cases += 1
    # 6要求の連続2周期の全パターン。発生元での取りこぼし/持越しがないこと。
    handshake_cases = 0
    for first in itertools.product((False, True), repeat=6):
        for second in itertools.product((False, True), repeat=6):
            flags = [False] * 6
            for events in (first, second):
                flags = [old or event for old, event in zip(flags, events)]
                assert tuple(flags) == events
                # HMIの番号選択後に、この6要求だけを確実に解除。
                values = {'P_On': True, **{b.request(n): x for n, x in zip(NUMBERS, flags)}}
                b.h.apply_coils(reset_row, values)
                flags = [values[b.request(n)] for n in NUMBERS]
                assert not any(flags)
                handshake_cases += 1
    ladders = {}
    for name in PREV['ladder_counts']:
        text = changes.get(name, raw[name].decode('utf-8-sig'))
        ladders[name] = [json.loads(l) for l in text.splitlines() if l.strip()]
    assert ladders[fh_name] == changed_fh and ladders[hmi_name] == after_hmi
    assert sum(1 for r in ladders[hmi_name] for c in r['CLs'] if b.message_number(c) is not None) == 121
    for name, rows in ladders.items():
        if name != hmi_name:
            assert not any(b.message_number(c) is not None for r in rows for c in r['CLs'])
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
                assert z.read(name) == before.read(name)
    report = {'source': str(SOURCE), 'staged': str(STAGED), 'destination': str(DEST),
              'source_sha256': PREV['output_sha256'], 'output_sha256': hashlib.sha256(STAGED.read_bytes()).hexdigest(),
              'names': PREV['names'], 'changed_entries': list(changes), 'fixes': fixes,
              'checks': {'original_g_geometry_restored_rows': 4, 'wiring_cases': wiring_cases,
                         'two_cycle_request_cases': handshake_cases, 'hmi_moves': 121,
                         'all_other_archive_entries_preserved': True, 'existing_Up_ids_preserved': True,
                         'stop_output_task_declarations_and_io_unchanged': True},
              'ladder_counts': {n: len(rr) for n, rr in ladders.items()},
              'native_validation': {}, 'application_build': {'verified': False},
              'hardware_transfer_performed': False}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'staged': str(STAGED), 'checks': report['checks'], 'rungs': sum(report['ladder_counts'].values())}, ensure_ascii=False))


def publish():
    report = json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert report['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in report['native_validation'].values())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest() == report['output_sha256']
    with STAGED.open('rb') as src, DEST.open('xb') as target:
        shutil.copyfileobj(src, target)
    print('保存完了：' + str(DEST))


if __name__ == '__main__':
    publish() if '--publish' in sys.argv else build()
