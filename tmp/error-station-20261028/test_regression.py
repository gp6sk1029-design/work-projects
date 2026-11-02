"""原回路と実際の生成回路を、保持値・RESETを含めて直接照合する。"""
import itertools
import json
import zipfile
import build_g as b

report = json.loads(b.REPORT.read_text(encoding='utf-8-sig'))
with zipfile.ZipFile(report['staged']) as z:
    errors = [json.loads(l) for l in z.read(b.NAMES['error']).decode('utf-8-sig').splitlines() if l.strip()]
    st7 = [json.loads(l) for l in z.read(b.NAMES['st7']).decode('utf-8-sig').splitlines() if l.strip()]
old_errors = b.ROWS[b.NAMES['error']]
source_indices = {'ST1_A': [11], 'ST1_B': [13], 'ST2_A': [18], 'ST3_A': [17, 19],
                  'ST4_A': [20], 'ST5_A': [12], 'ST5_B': [14], 'ST6_A': [21], 'ST7_A': [22]}
blocks = {}
for station, label in b.LABELS.items():
    start = next(i for i, r in enumerate(errors) if r.get('CMT', '').startswith('#' + label))
    stop = start + 1
    while stop < len(errors) and not errors[stop].get('CMT', '').startswith('#'):
        # 次のST見出し直前。ST7の後は原本FHリセット行なので停止する。
        if errors[stop] == old_errors[15]:
            break
        stop += 1
    blocks[station] = errors[start:stop]

cases = 0
for station, source in source_indices.items():
    original = [old_errors[i] for i in source]
    raw_keys = sorted({c['Var'] for r in original for c in r['CLs'] if c.get('__type') in ('LD', 'FB')
                       and not c.get('Var', '').startswith('Error_M[')})
    for history in itertools.product((False, True), repeat=len(b.ACTIVE[station])):
        for input_values in itertools.product((False, True), repeat=len(raw_keys)):
            v = dict(zip(raw_keys, input_values))
            new = {**v, **{b.bit(station, i): state for i, state in zip(b.ACTIVE[station], history)}}
            new[b.bit(station, 0)] = any(history)
            old = dict(v)
            for old_index, (mapped_station, mapped_cause) in b.MAPPING.items():
                if mapped_station == station:
                    old[f'Error_M[{old_index}]'] = any(history) if mapped_cause == 0 else new[b.bit(station, mapped_cause)]
            # ST7は元のSET保持信号と、その理由保持が同時に更新される。
            attribution_states = ((False, False), (True, False), (False, True), (True, True)) if station == 'ST7_A' else ((False, False),)
            for s3, s4 in attribution_states:
                if station == 'ST7_A' and bool(s3 or s4) != v['ST7_A_Dis2_M[11]']:
                    continue
                vv = dict(new)
                vv.update({'Error_ST7_A_Source_M[3]': s3, 'Error_ST7_A_Source_M[4]': s4})
                oo = dict(old)
                for r in original:
                    b.apply_coils(r, oo)
                for r in blocks[station]:
                    b.apply_coils(r, vv)
                for old_index, (mapped_station, mapped_cause) in b.MAPPING.items():
                    if mapped_station == station:
                        assert oo[f'Error_M[{old_index}]'] == vv[b.bit(station, mapped_cause)], (station, v, history)
                for key in {c['Var'] for r in original for c in r['CLs'] if c.get('__type') == 'ST'
                            and c.get('Var', '').startswith(('Pause[', 'Out_TDC_Stop'))}:
                    assert oo.get(key, False) == vv.get(key, False), (station, key)
                cases += 1

# 元のST7分岐そのものを通して、追加した理由記録との対応を検証する。
source_cases = 0
source_keys = ['ST7_A_Dis2_M[7]', 'Out_CYw_Ejc_Hldr_Feed_A_H_Done', 'Pause[13]', 'Up',
               'ST7_A_Dis2_M[8]', 'ST7_A_Dis2_M[12]', 'TimerQ_In_Sen_Work_A_Pos_07',
               'Station_A_Data[7].Work_On', 'TimerQ_In_Sen_NG2_Tray_B_Full']
for values in itertools.product((False, True), repeat=len(source_keys)):
    for prior3, prior4 in itertools.product((False, True), repeat=2):
        v = dict(zip(source_keys, values))
        v.update({'ST7_A_Dis2_M[11]': prior3 or prior4, 'Error_ST7_A_Source_M[3]': prior3,
                  'Error_ST7_A_Source_M[4]': prior4})
        original_v = dict(v)
        b.apply_coils(b.ROWS[b.NAMES['st7']][8], original_v)
        for row in st7[8:12]:
            b.apply_coils(row, v)
        for key in ('ST7_A_Dis2_M[8]', 'ST7_A_Dis2_M[9]', 'ST7_A_Dis2_M[10]', 'ST7_A_Dis2_M[11]'):
            assert v[key] == original_v[key], (key, values)
        assert v['ST7_A_Dis2_M[11]'] == (v['Error_ST7_A_Source_M[3]'] or v['Error_ST7_A_Source_M[4]'])
        source_cases += 1

# スコープ内の全新規参照に宣言があることと、I/O割付の完全一致を別検査する。
with zipfile.ZipFile(report['staged']) as z:
    tables = {n: z.read(n).decode('utf-8-sig') for n in report['changed_entries'] if b.TEXTS[n].startswith('[SLWD')}
for entry, scope in ((b.NAMES['error'], 'mode_vars'), (b.NAMES['st7'], 'movement_vars')):
    names = b.declarations(tables[b.NAMES[scope]])
    for row in errors if scope == 'mode_vars' else st7:
        for node in b.walk(row):
            var = node.get('Var', '').split('[', 1)[0].split('.', 1)[0]
            if var.startswith('Error_ST') or var == 'Error_Common_MessageActive':
                assert var in names, (scope, var)
at_count = 0
for entry, table in b.TEXTS.items():
    if not table.startswith('[SLWD'):
        continue
    old_at = {n: b.fields(l).get('AT') for n, l in b.declarations(table).items() if b.fields(l).get('AT')}
    new_at = {n: b.fields(l).get('AT') for n, l in b.declarations(tables.get(entry, table)).items() if b.fields(l).get('AT')}
    assert old_at == new_at
    at_count += len(old_at)
report['checks'].update({'original_vs_generated_station_cases': cases, 'original_st7_branch_cases': source_cases,
                         'io_assignment_count': at_count, 'new_reference_declarations_resolved': True})
b.REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'original_vs_generated_station_cases': cases, 'original_st7_branch_cases': source_cases,
                  'io_assignment_count': at_count}, ensure_ascii=False))
