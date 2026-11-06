"""ST案の条件・座標式を読み、16か所の対応を検算する。"""
from pathlib import Path
import re
import json
import hashlib

root = Path(r'C:\Users\SEIGI-N13\work-projects')
draft = root / 'outputs/box-layout-st-20261104/箱詰め4x4_5個_ST案.st'
source = Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261104C.smc2')
st = draft.read_text(encoding='utf-8')
st = re.sub(r'\(\*.*?\*\)', '', st, flags=re.S)
st = re.sub(r'//[^\n]*', '', st)
x_blocks = re.findall(r'(?:IF|ELSIF)\s+((?:\(Box_Total_CT = INT#\d+\)\s*(?:OR\s*)?)+)THEN\s+RCON2_2_OUT_TargetPos_mm\s*:=\s*(.*?);', st, re.S)
y_blocks = re.findall(r'(?:IF|ELSIF)\s+Box_Total_CT <= INT#(\d+) THEN\s+RCON2_3_OUT_TargetPos_mm\s*:=\s*(.*?);', st, re.S)
y_else = re.search(r'ELSE\s+RCON2_3_OUT_TargetPos_mm\s*:=\s*(.*?);', st, re.S).group(1)
assert len(x_blocks) == 4 and len(y_blocks) == 3
assert '(Box_Total_CT >= INT#5)' in st and '(Box_Total_CT <= INT#80)' in st
assert '((Box_Total_CT MOD INT#5) = INT#0)' in st
assert 'IF Box_PackPos_Calc AND Box_PackCount_Valid THEN' in st

def coordinate(expr, axis, start, pitch):
    expr = expr.replace(f'HMI_RCON2_{axis}_OUT_TargetPos[3]', repr(start))
    expr = expr.replace(f'HMI_RCON2_{axis}_OUT_TargetPos[4]', f'({pitch})')
    expr = expr.replace('LREAL#', '')
    assert re.fullmatch(r'[\d\s.()+*\-]+', expr), expr
    return eval('(' + expr + ')', {'__builtins__': {}}, {})

counts = []
for condition, _ in x_blocks:
    counts += list(map(int, re.findall(r'INT#(\d+)', condition)))
assert sorted(counts) == list(range(5, 81, 5))
assert len(set(counts)) == 16
checked = 0
for x_start, y_start, x_pitch, y_pitch in [(100., 200., 12.5, 20.), (100., 200., -12.5, -20.), (0., 0., 0., 0.)]:
    for n, count in enumerate(range(5, 81, 5)):
        matches = [expr for cond, expr in x_blocks if count in map(int, re.findall(r'INT#(\d+)', cond))]
        assert len(matches) == 1
        y_expr = next((expr for upper, expr in y_blocks if count <= int(upper)), y_else)
        x = coordinate(matches[0], 2, x_start, x_pitch)
        y = coordinate(y_expr, 3, y_start, y_pitch)
        assert x == x_start + (n % 4) * x_pitch
        assert y == y_start + (n // 4) * y_pitch
        checked += 1
invalid = [-5, 0, 1, 4, 6, 79, 81, 85]
assert all(not (5 <= c <= 80 and c % 5 == 0) for c in invalid)
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_hash == '7eff9e409610d791c10e182d68ebff31055d0b854ea0532b016fbd1087b648ee'
result = {'座標式確認件数': checked, '有効位置数': 16, '無効カウント確認数': len(invalid), '元ファイルSHA256': source_hash, '元ファイル変更': False, 'Sysmacコンパイル': '未実施'}
(draft.parent / '検算結果.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
