"""６軸展開の対応・保持範囲・定数属性と、限定的な接点動作を検査する。"""
import collections
import copy
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
import build_f as b

sys.stdout.reconfigure(encoding="utf-8")
report = json.loads(b.REPORT.read_text(encoding="utf-8-sig"))
with zipfile.ZipFile(b.SOURCE) as z, zipfile.ZipFile(b.STAGED) as o:
    old = {n: z.read(n) for n in z.namelist()}
    new = {n: o.read(n) for n in o.namelist()}


def name(key):
    return next(n for n in old if n.endswith(b.IDS[key]))


def rows(table):
    return [json.loads(l) for l in table[name("rcon")].decode("utf-8-sig").splitlines() if l.strip()]


def at_map(table):
    result = {}
    for n, raw in table.items():
        if not raw.startswith((b"[SLWD", b"\xef\xbb\xbf[SLWD")):
            continue
        for l in raw.decode("utf-8-sig").splitlines():
            if l.startswith("++D="):
                d = b.parse_decl(l)
                if "AT" in d:
                    result[(n, d["N"])] = (d["D"], d["AT"])
    return result


def no_comment_and_ids(row):
    row = copy.deepcopy(row)
    row.pop("CMT", None)
    for node in b.walk(row):
        node.pop("Id", None)
    return row


assert at_map(old) == at_map(new)
for n, raw in old.items():
    if n.endswith((".dat", ".oem")):
        assert new[n] == raw
    # すべての他ラダーをバイト保持。型定義や既存制御は変更しない。
    if n in report["ladder_counts"] and n != name("rcon"):
        assert new[n] == raw
original_rows, output_rows = rows(old), rows(new)
assert len(original_rows) == 46 and len(output_rows) == 246
global_original = b.declarations(old[name("globals")].decode("utf-8-sig"))
for axis in range(1, 7):
    block = output_rows[(axis - 1) * 40:axis * 40]
    mapping = {} if axis == 1 else {**b.source_map(axis, global_original), "RCON1_1_TON": f"RCON1_{axis}_TON", "RCON1_1_TOF": f"RCON1_{axis}_TOF"}
    for before, after in zip(original_rows[:40], block):
        expect = copy.deepcopy(before)
        if axis != 1:
            for node in b.walk(expect):
                if isinstance(node.get("Var"), str):
                    node["Var"] = b.transform_var(node["Var"], axis, mapping)
        assert no_comment_and_ids(expect) == no_comment_and_ids(after)
    for i in (0, 1, 2, 3, 4, 20, 21, 22, 23, 24):
        assert block[i]["CLs"][0]["Var"] == "P_Off"
    assert block[19]["CLs"][0]["Var"] == "M9999" and block[19]["CLs"][0]["Not"] is True
    # 指令・入力の構造体は当該軸のみ参照。
    indices = {int(x) for x in re.findall(r"RCON1_(?:OUT|IN)\[(\d+)\]", json.dumps(block))}
    assert indices == {axis}, (axis, indices)
for before, after in zip(original_rows[40:], output_rows[240:]):
    assert no_comment_and_ids(before) == no_comment_and_ids(after)
    assert before["CLs"][0]["TXT"] == after["CLs"][0]["TXT"]

global_after = b.declarations(new[name("globals")].decode("utf-8-sig"))
assert len(global_after) - len(global_original) == 135
assert all(b.parse_decl(global_after[var]).get("Const") == "0" and b.parse_decl(global_after[var]).get("RO") == "0" for var in report["global_added"])
before_meta = ET.fromstring(old[name("metadata")].decode("utf-8-sig"))
after_meta = ET.fromstring(new[name("metadata")].decode("utf-8-sig"))
before_nodes = {e.get("Name"): e.attrib for e in before_meta.iter("Variable")}
after_nodes = {e.get("Name"): e.attrib for e in after_meta.iter("Variable")}
assert set(after_nodes) - set(before_nodes) == set(report["global_added"])
for var, attributes in before_nodes.items():
    before, after = dict(attributes), dict(after_nodes[var])
    before.pop("Comment", None)
    after.pop("Comment", None)
    assert before == after, var
assert len(after_nodes) == len([e for e in after_meta.iter("Variable")])
ids = [e["Id"] for e in after_nodes.values()]
assert len(ids) == len(set(ids))
for var in report["global_added"]:
    assert after_nodes[var]["IsConstant"] == after_nodes[var]["IsReadOnly"] == "false"
    assert after_nodes[var]["Address"] == "new_Controller_0." + var


def energized(row, values, events=None):
    """タイマー出力と立上りを外部で与える配線モデル。実時間/PLCスキャンは検証しない。"""
    events = events or {}
    graph = collections.defaultdict(list)
    max_y = max([c.get("Y", 0) for c in row["CLs"]] + [w.get("Y", 0) + 1 for w in row.get("VLs", [])])
    for c in row["CLs"]:
        condition = True
        if c["__type"] == "LD":
            condition = values.get(c["Var"], False)
            if c["Var"] == "P_Off":
                condition = False
            if c.get("Not"):
                condition = not condition
        elif c["__type"] == "FB":
            condition = values.get(c["Var"] + ".Q", False)
        elif c.get("Name") == "Up":
            condition = events.get(c["Id"], False)
        if condition:
            x, y = c.get("X", 0), c.get("Y", 0)
            graph[(x, y)].append((x + 1, y))
    for w in row.get("VLs", []):
        a = (w.get("X", 0), w.get("Y", 0))
        dest = (a[0], a[1] + 1)
        graph[a].append(dest)
        graph[dest].append(a)
    reached = {(0, y) for y in range(max_y + 1)}
    queue = list(reached)
    while queue:
        for dest in graph[queue.pop()]:
            if dest not in reached:
                reached.add(dest)
                queue.append(dest)
    return {c["Var"]: (c.get("X", 0), c.get("Y", 0)) in reached for c in row["CLs"] if c["__type"] == "ST"}


cases = collections.Counter()
for axis in range(1, 7):
    block = output_rows[(axis - 1) * 40:axis * 40]
    for ready, servo, alarm, emergency in itertools.product((False, True), repeat=4):
        values = {f"RCON1_{axis}_IN_ControllerReady": ready, f"RCON1_{axis}_IN_ServoReady": servo,
                  f"RCON1_IN[{axis}].Status.Alarm": alarm, f"RCON1_{axis}_IN_EmergencyStop": emergency}
        assert energized(block[37], values)[f"RCON1_{axis}_Ready"] == (ready and servo and not alarm and not emergency)
        cases["軸別Ready条件"] += 1
    for active, sensor, pulse, timer in itertools.product((False, True), repeat=4):
        values = {f"RCON1_{axis}_M[1]": active, f"RCON1_{axis}_TOF[1].Q": timer,
                  "TimerQ_In_SenCY_NG1_Pick_A_H": sensor, "TimerQ_In_SenCY_NG1_Pick_B_H": sensor}
        up = next(c for c in block[5]["CLs"] if c.get("Name") == "Up")["Id"]
        expect = active and sensor and pulse and timer and axis <= 2
        assert energized(block[5], values, {up: pulse})[f"RCON1_OUT[{axis}].Control.Start"] == expect
        cases["開始インターロック・未確定禁止"] += 1
    for emergency in (False, True):
        for i, field in ((9, "ServoOn"), (19, "BrakeRelease")):
            assert energized(block[i], {"M9999": emergency})[f"RCON1_OUT[{axis}].Control.{field}"] == (not emergency)
            cases["承認済みサーボ・強制解除条件"] += 1
    for start, done, hold, expired, pulse in itertools.product((False, True), repeat=5):
        values = {f"RCON1_{axis}_M[1]": start, f"RCON1_{axis}_IN_PositionDone": done,
                  f"RCON1_{axis}_M[2]": hold, f"RCON1_{axis}_TON[2].Q": expired}
        up = next(c for c in block[39]["CLs"] if c.get("Name") == "Up")["Id"]
        assert energized(block[39], values, {up: pulse})[f"RCON1_{axis}_M[2]"] == ((start and done and pulse or hold) and not expired)
        cases["軸別完了保持"] += 1
    for status in b.STATUS:
        index = list(b.STATUS).index(status)
        # 順序は入力表の対応を命令の構造体メンバー名から特定。
        row = next(r for r in block[25:37] if any(c.get("Var") == f"RCON1_{axis}_IN_{status}" for c in r["CLs"]))
        for flag in (False, True):
            expect = flag and status != "PushMiss"
            result = energized(row, {f"RCON1_IN[{axis}].Status.{status}": flag})
            assert result[f"RCON1_{axis}_IN_{status}"] == expect
            cases["軸別状態入力"] += 1

# 全軸のControl項目が各１か所だけで書かれること。共通STは実I/Oへの書込みだけで変更していない。
for axis in range(1, 7):
    writers = collections.Counter(c["Var"] for row in output_rows[:240] for c in row["CLs"] if c.get("__type") == "ST" and c.get("Var", "").startswith(f"RCON1_OUT[{axis}].Control."))
    assert len(writers) == 15 and set(writers.values()) == {1}

report["delta_audit"] = {
    "limited_boolean_cases": dict(cases), "total_cases": sum(cases.values()),
    "physical_at_declarations_unchanged": len(at_map(old)), "all_other_ladders_byte_identical": True,
    "all_common_ist_texts_unchanged": True, "all_axis_maps_verified": True,
    "axis1_logic_unchanged": True, "all_existing_metadata_except_comment_unchanged": True,
}
b.REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report["delta_audit"], ensure_ascii=False, indent=2))
