"""ST2高さ検査の重複工程を修正した確認用コピーを生成する。"""
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

src = Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261021A.smc2')
dst = src.with_name(src.stem + '_ST2工程番号修正_確認用.smc2')
report = dst.with_suffix('.変更内容.txt')
assert not dst.exists() and not report.exists(), '既存出力を上書きしない'
before_hash = hashlib.sha256(src.read_bytes()).hexdigest()
prefix = 'a3ddffe8-0ae2-4572-b788-7dad5dced47d/'
ladder = prefix + '910f90f5-80d6-4e6f-ba4f-5e9862fd5171.xml'
variables = prefix + '86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml'
pat = re.compile(r'ST2_A_Hgt_M\[(\d+)\]')
with ZipFile(src) as zin:
    payload = {i.filename: zin.read(i) for i in zin.infolist()}
    ladder_encoding = 'utf-8-sig' if payload[ladder].startswith(b'\xef\xbb\xbf') else 'utf-8'
    variables_encoding = 'utf-8-sig' if payload[variables].startswith(b'\xef\xbb\xbf') else 'utf-8'
    original_ladder = payload[ladder].decode(ladder_encoding)
    rungs = [json.loads(x) for x in original_ladder.splitlines() if x.strip()]
    assert len(rungs) == 9
    writes8 = [(r, c) for r, rung in enumerate(rungs) for c, cell in enumerate(rung['CLs'])
               if cell.get('__type') == 'ST' and cell.get('Var') == 'ST2_A_Hgt_M[8]']
    assert len(writes8) == 2 and [x[0] for x in writes8] == [5, 6]
    keep_rung, keep_cell = writes8[0]
    lines = original_ladder.splitlines(keepends=True)
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    assert len(nonempty) == len(rungs)
    changes = []
    for rung_no, line_no in enumerate(nonempty):
        matches = list(pat.finditer(lines[line_no]))
        # 最初の8出力だけ残す。他の8参照は高さ検査開始工程を参照する。
        preserve = None
        if rung_no == keep_rung:
            assert len([m for m in matches if m.group(1) == '8']) == 2
            preserve = [m.start() for m in matches if m.group(1) == '8'][-1]
        def replace(m):
            n = int(m.group(1))
            if n < 8 or m.start() == preserve:
                return m.group(0)
            assert n <= 11
            changes.append((rung_no, n, n + 1))
            return f'ST2_A_Hgt_M[{n + 1}]'
        lines[line_no] = pat.sub(replace, lines[line_no])
    after_ladder = ''.join(lines)
    # 配置・命令・他変数を変更していないことを構造比較で検査する。
    after_rungs = [json.loads(x) for x in after_ladder.splitlines() if x.strip()]
    expected = json.loads(json.dumps(rungs))
    for rn, rung in enumerate(expected):
        for cn, cell in enumerate(rung['CLs']):
            var = cell.get('Var', '')
            m = pat.fullmatch(var)
            if m and int(m.group(1)) >= 8 and (rn, cn) != (keep_rung, keep_cell):
                cell['Var'] = f'ST2_A_Hgt_M[{int(m.group(1)) + 1}]'
    assert expected == after_rungs
    writers = [(rn, cell['Var']) for rn, rung in enumerate(after_rungs)
               for cell in rung['CLs'] if cell.get('__type') == 'ST' and pat.fullmatch(cell.get('Var', ''))]
    writer_names = [name for _, name in writers]
    assert len(writer_names) == len(set(writer_names)) == 12
    assert set(writer_names) == {f'ST2_A_Hgt_M[{i}]' for i in range(1, 13)}
    vartext = payload[variables].decode(variables_encoding)
    decl = re.search(r'(?m)^.*N=ST2_A_Hgt_M[^\r\n]*', vartext)
    assert decl and 'ARRAY[0..99]' in decl.group(0)
    comments = re.search(r'(<ECs>)(.*?)(</ECs>)', decl.group(0))
    assert comments
    old = comments.group(2)
    keys = re.findall(r'<EC EK="\[(\d+)\]" C="([^"]*)" />', old)
    assert {int(k) for k, _ in keys if int(k) >= 8} == {8, 9, 10, 11}
    shifted = re.sub(r'EK="\[(\d+)\]"', lambda m: f'EK="[{int(m.group(1)) + (1 if int(m.group(1)) >= 8 else 0)}]"', old)
    shifted += '<EC EK="[8]" C="ワーク無判定" />'
    replacement = decl.group(0)[:comments.start(2)] + shifted + decl.group(0)[comments.end(2):]
    after_vars = vartext[:decl.start()] + replacement + vartext[decl.end():]
    payload[ladder] = after_ladder.encode(ladder_encoding)
    payload[variables] = after_vars.encode(variables_encoding)
    with ZipFile(dst, 'w') as zout:
        zout.comment = zin.comment
        for info in zin.infolist():
            zout.writestr(info, payload[info.filename])
with ZipFile(src) as zin, ZipFile(dst) as zout:
    assert zout.testzip() is None
    assert zin.namelist() == zout.namelist()
    changed_entries = [n for n in zin.namelist() if zin.read(n) != zout.read(n)]
    assert set(changed_entries) == {ladder, variables}
assert hashlib.sha256(src.read_bytes()).hexdigest() == before_hash
summary = '\n'.join([
    'ST2_A_Hgt_M 工程番号変更（Sysmacでの確認用）',
    '原本：' + str(src),
    '出力：' + str(dst),
    '最初の[8]出力（ワーク有無判定）は維持。コメントは「ワーク無判定」。',
    '高さ検査開始の[8]→[9]、従来[9]→[10]、[10]→[11]、[11]→[12]。',
    '先行するワーク有無判定回路のb接点[8]も、検査開始工程参照のため[9]へ変更。',
    '自己保持・次工程条件・完了判定の参照先も同時に変更。',
    '従来[8]～[11]のコメント本文は維持して[9]～[12]へ移動。',
    '既存コメントの動作名称そのものの正否や、工程条件の妥当性は今回変更しない。',
    '配列型ARRAY[0..99] OF Boolは変更なし。',
    f'変数参照の変更数：{len(changes)}',
    '静的確認：工程コイル[1]～[12]に重複なし、JSON解析成功、ZIP検査成功。',
    'アーカイブ内の変更は対象ラダーと変数コメントの2エントリのみ。その他は全バイト一致。',
    '重要：Sysmac Studioで開く・ビルド・動作検証は未実施。実機へ転送しないこと。',
    '開いたプロジェクトと比較し、特にワーク無し分岐と検査完了条件を確認すること。',
    '原本SHA256：' + before_hash,
    '出力SHA256：' + hashlib.sha256(dst.read_bytes()).hexdigest(),
])
report.write_text(summary + '\n', encoding='utf-8-sig')
print(summary)
