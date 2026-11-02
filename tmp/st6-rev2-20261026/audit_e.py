"""E版の差分・型・割付と、変更した接点回路の限定ブール検査。"""
import collections
import copy
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
import build_e as b

sys.stdout.reconfigure(encoding="utf-8")
report = json.loads(b.REPORT.read_text(encoding="utf-8-sig"))
with zipfile.ZipFile(b.SOURCE) as z, zipfile.ZipFile(b.STAGED) as output:
    old = {n: z.read(n) for n in z.namelist()}
    new = {n: output.read(n) for n in output.namelist()}


def name(key):
    return next(n for n in old if n.endswith(b.IDS[key]))


def rows(key, table=new):
    return [json.loads(s) for s in table[name(key)].decode("utf-8-sig").splitlines() if s.strip()]


def at_map(table):
    result = {}
    for n, raw in table.items():
        if not raw.startswith((b"[SLWD", b"\xef\xbb\xbf[SLWD")):
            continue
        for line in raw.decode("utf-8-sig").splitlines():
            if line.startswith("++D="):
                decl = b.parse_decl(line)
                if "AT" in decl:
                    result[(n, decl["N"])] = (decl["D"], decl["AT"])
    return result


def value(expr, values):
    if expr == "TRUE":
        return True
    if expr == "FALSE":
        return False
    if expr.startswith("INT#"):
        return int(expr[4:])
    return values.get(expr, False)


def energized(row, values):
    """配線と比較接点だけ評価。Upは無パルス、FBは時間動作を模擬しない。"""
    graph = collections.defaultdict(list)
    max_y = max([c.get("Y", 0) for c in row["CLs"]] + [w.get("Y", 0) + 1 for w in row.get("VLs", [])])
    for c in row["CLs"]:
        x, y = c.get("X", 0), c.get("Y", 0)
        condition = True
        if c["__type"] == "LD":
            condition = bool(value(c["Var"], values))
            if c.get("Not"):
                condition = not condition
        elif c.get("Name") == "=":
            args = {p["Arg"]: p.get("Var", "") for p in c["In"] if p["__type"] == "PRM"}
            condition = value(args["In1"], values) == value(args["In2"], values)
        elif c.get("Name") == "Up":
            condition = False
        if condition:
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


assert at_map(old) == at_map(new)
assert all(raw == new[n] for n, raw in old.items() if n.endswith(".dat"))
assert len(rows("output")) == 316
assert all(a == c for i, (a, c) in enumerate(zip(old[name("output")].decode("utf-8-sig").splitlines(), new[name("output")].decode("utf-8-sig").splitlines())) if i not in (94, 97, 142))

# ST4とST6の変更箇所は、承認済みの対応以外に命令や結線を変えていない。
for i, (original, updated) in enumerate(zip(rows("st4", old), rows("st4"))):
    expect = copy.deepcopy(original)
    if i == 7:
        next(c for c in expect["CLs"] if c.get("Var") == "ST4_A_Rev1_M[10]").pop("RS")
    if i in (9, 10):
        for node in b.walk(expect):
            if isinstance(node.get("Var"), str):
                node["Var"] = node["Var"].replace("Rev_02_Chk", "Rev_01_Chk")
    assert b.shape(expect) == b.shape(updated)
for i, (original, updated) in enumerate(zip(rows("st6", old), rows("st6"))):
    expect = b.mapped(original)
    if i == 7:
        next(c for c in expect["CLs"] if c.get("Var") == "ST6_A_Rev2_M[10]").pop("RS")
    assert b.shape(expect) == b.shape(updated)

counts = collections.Counter()
for key, prefix, bit, pos in [("st4", "ST4_A_Rev1_M", 8, 4), ("st6", "ST6_A_Rev2_M", 12, 6)]:
    row = rows(key)[7]
    busy = "ST4_A_Rev1_Busy" if key == "st4" else "ST6_A_Rev2_Busy"
    for flags in itertools.product((False, True), repeat=7):
        sensor, work, good, prior, running, hold, pause = flags
        values = {f"TimerQ_In_Sen_Work_A_Pos_{pos:02}": sensor, f"Station_A_Data[{pos}].Work_On": work,
                  f"Station_A_Data[{pos}].Total_Judge": 1 if good else 9,
                  prefix + "[6]": prior, busy: running, prefix + "[7]": hold, f"Pause[{bit}]": pause}
        result = energized(row, values)
        enable = (prior and running or hold) and not pause
        assert result[prefix + "[8]"] == (enable and sensor and work and good)
        assert result[prefix + "[9]"] == (enable and (not sensor and not work or sensor and work and not good))
        assert result[prefix + "[10]"] == (enable and sensor != work)
        counts["ワーク判定・通常コイル"] += 1

for a_trigger, a_hold, s_trigger, s_hold, reset in itertools.product((False, True), repeat=5):
    values = {"ST4_A_Rev1_M[10]": a_trigger, "Error_M[8]": a_hold, "ST6_A_Rev2_M[10]": s_trigger,
              "Error_M[12]": s_hold, "In_Sw_RESET": reset, "ST4_A_Rev1_M[9]": True, "ST6_A_Rev2_M[9]": True}
    for row_index, bit, trigger, hold in [(20, 8, a_trigger, a_hold), (21, 12, s_trigger, s_hold)]:
        result = energized(rows("error")[row_index], values)
        expect = (trigger or hold) and not reset
        assert result[f"Error_M[{bit}]"] == expect
        assert result[f"Pause[{bit}]"] == expect
        assert result["Out_TDC_Stop"] == expect
    counts["ST4・ST6異常分離"] += 1

for start, door, emergency in itertools.product((False, True), repeat=3):
    for pause in range(13):
        for blocking in range(13):
            values = {"In_Sw_START": start, "AutoMode": True, "In_Sen_DOOR_01": door, "M9999": emergency,
                      **{f"Pause[{i}]": i == pause for i in range(1, 13)},
                      **{f"Error_M[{i}]": i == blocking for i in range(1, 13)}}
            result = energized(rows("error")[-1], values)
            permission = start and not door and not emergency and blocking == 0
            for i in range(1, 13):
                assert result[f"Pause[{i}]"] == (permission and i == pause)
            counts["再開許可・Pause解除"] += 1

cv = rows("cv")[0]
all_true = {"Auto_A_Start": True, "ST0_A_Sup_End": True, "ST1_A_Ca1_End": True,
            "ST2_A_Hgt_End": True, "ST3_A_Dis1_End": True, "ST5_A_Ca2_End": True,
            "ST7_Ins_Cv_Rdy": True, "ST6_Ins_Cv_Rdy": True}
for done, hold, busy in itertools.product((False, True), repeat=3):
    values = {**all_true, "ST6_A_Rev2_End": done, "Ins_A_End": hold, "Ins_A_Cv_M[3]": busy}
    assert energized(cv, values)["Ins_A_End"] == ((done or hold) and not busy)
    counts["ST6完了待ち"] += 1

# 追加Axis001処理の全変数/パラメータがコピー元の対応形。元４行は原文のまま。
for source, target in zip(rows("motion", old), rows("motion")[4:]):
    expect = b.mapped(source)
    if expect["CLs"][0]["__type"] == "IST":
        expect["CLs"][0]["EID"] = report["inline_eid"]
    assert b.shape(expect) == b.shape(target)

before_meta = ET.fromstring(old[name("metadata")].decode("utf-8-sig"))
after_meta = ET.fromstring(new[name("metadata")].decode("utf-8-sig"))
old_meta = {v.get("Name"): v.attrib for v in before_meta.iter("Variable")}
new_meta = {v.get("Name"): v.attrib for v in after_meta.iter("Variable")}
assert all(new_meta[k] == v for k, v in old_meta.items())
assert set(new_meta) - set(old_meta) == {n for n, _ in b.GLOBAL_PAIRS.values()}
assert new_meta["HMI_Stm_A_Rev_Axis001_MovePos_Degree"]["DataTypeName"] == "Double(99)"
assert len([v["Id"] for v in new_meta.values()]) == len({v["Id"] for v in new_meta.values()})

report["delta_audit"] = {"limited_boolean_cases": dict(counts), "total_cases": sum(counts.values()),
                         "physical_at_declarations_unchanged": len(at_map(old)), "old_hmi_variable_metadata_unchanged": len(old_meta),
                         "approved_st4_changes_only": True, "st6_mapping_and_motion_mapping_verified": True}
b.REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report["delta_audit"], ensure_ascii=False, indent=2))
