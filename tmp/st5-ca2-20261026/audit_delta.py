"""追加差分の静的照合と、接点結線の限定ブールモデル検査（PLC実行試験ではない）。"""
from pathlib import Path
import collections
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
import build_c as b

sys.stdout.reconfigure(encoding="utf-8")
report = json.loads(b.REPORT.read_text(encoding="utf-8-sig"))
with zipfile.ZipFile(b.SOURCE) as source, zipfile.ZipFile(b.STAGED) as staged:
    old = {n: source.read(n) for n in source.namelist()}
    new = {n: staged.read(n) for n in staged.namelist()}

def name(key):
    return next(n for n in old if n.endswith(b.IDS[key] + ".xml"))

def rows(key, table=new):
    return [json.loads(x) for x in table[name(key)].decode("utf-8-sig").splitlines() if x.strip()]

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

assert at_map(old) == at_map(new)
assert all(old[n] == new[n] for n in old if n.endswith(".dat"))
assert old[name("st1")] == new[name("st1")]
assert len(rows("output")) == 316
assert rows("output")[137] == rows("output", old)[137]
for original, changed in zip(rows("fh", old), rows("fh")[8:]):
    expected = b.converted(original)
    for node in b.walk(expected):
        if node.get("Var") in ("INT#113", "INT#114", "INT#115"):
            node["Var"] = "INT#" + str(int(node["Var"].split("#")[1]) + 5)
    assert b.shape(expected) == b.shape(changed)
for original, changed in zip(rows("st5", old), rows("st5")):
    assert b.shape(b.converted(original)) == b.shape(changed)

# HMI変数名／GUIDの追加は６個だけ。元のノードを変更していない。
meta_old = ET.fromstring(old[name("metadata")].decode("utf-8-sig"))
meta_new = ET.fromstring(new[name("metadata")].decode("utf-8-sig"))
old_vars = {v.get("Name"): v.attrib for v in meta_old.iter("Variable")}
new_vars = {v.get("Name"): v.attrib for v in meta_new.iter("Variable")}
assert all(new_vars[k] == v for k, v in old_vars.items())
assert set(new_vars) - set(old_vars) == {v[0] for v in b.GLOBAL_PAIRS.values()}
ids = [v.get("Id") for v in meta_new.iter("Variable") if v.get("Id")]
assert len(ids) == len(set(ids))
new_function_ids = [n["Id"] for r in rows("fh")[8:] for n in b.walk(r) if "Id" in n]
old_function_ids = {n["Id"] for r in rows("fh", old) for n in b.walk(r) if "Id" in n}
assert len(new_function_ids) == len(set(new_function_ids)) and not set(new_function_ids) & old_function_ids

# 番号117～121が元ラダーのINT定数で未使用であることを限定的に確認する。
for n in report["ladder_counts"]:
    text = old[n].decode("utf-8-sig")
    assert not re.search(r'INT#(?:117|118|119|120|121)(?!\d)', text)

def energized(row, values):
    """配線上の通電可否だけを検査する。タイマー/FBの時間動作は模擬しない。"""
    graph = collections.defaultdict(list)
    max_y = max([c.get("Y", 0) for c in row["CLs"]] + [w.get("Y", 0) + 1 for w in row.get("VLs", [])])
    for cell in row["CLs"]:
        x, y = cell.get("X", 0), cell.get("Y", 0)
        cond = True
        if cell["__type"] in ("LD", "FB"):
            cond = values.get(cell.get("Var"), False)
            if cell.get("Not"):
                cond = not cond
        if cond:
            graph[(x, y)].append((x + 1, y))
    for wire in row.get("VLs", []):
        a = (wire.get("X", 0), wire.get("Y", 0))
        c = (a[0], a[1] + 1)
        graph[a].append(c)
        graph[c].append(a)
    reached = {(0, y) for y in range(max_y + 1)}
    pending = list(reached)
    while pending:
        for target in graph[pending.pop()]:
            if target not in reached:
                reached.add(target)
                pending.append(target)
    return {(c["Var"], c.get("Y", 0)): (c.get("X", 0), c.get("Y", 0)) in reached
            for c in row["CLs"] if c["__type"] == "ST"}

cases = collections.Counter()
cv = rows("cv")[0]
keys = ["Auto_A_Start", "ST0_A_Sup_End", "ST1_A_Ca1_End", "ST2_A_Hgt_End", "ST3_A_Dis1_End", "ST5_A_Ca2_End", "ST6_Ins_Cv_Rdy", "ST7_Ins_Cv_Rdy", "Ins_A_End", "Ins_A_Cv_M[3]"]
for flags in itertools.product((False, True), repeat=len(keys)):
    values = dict(zip(keys, flags))
    expect = (all(values[k] for k in keys[:8]) or values["Ins_A_End"]) and not values["Ins_A_Cv_M[3]"]
    assert energized(cv, values)[("Ins_A_End", 0)] == expect
    cases["コンベア完了接点"] += 1

error = rows("error")[11]
keys = ["FH_5552_10_A_Auto", "Error_TON[2]", "FH_Line0_Error_Status_1", "FH_Line1_Error_Status_1", "FH_Line2_Error_Status_1", "FH_Line3_Error_Status_1", "ST1_A_Ca1_M[6]", "FH_A_ST5_Auto", "Error_TON[4]", "ST5_A_Ca2_M[6]", "Error_M[3]", "In_Sw_RESET"]
for flags in itertools.product((False, True), repeat=len(keys)):
    values = dict(zip(keys, flags))
    expect = (values[keys[0]] and values[keys[1]] or any(values[k] for k in keys[2:7]) or values[keys[7]] and values[keys[8]] or values[keys[9]] or values[keys[10]]) and not values[keys[11]]
    actual = energized(error, values)
    assert actual[("Error_M[3]", 0)] == expect
    assert actual[("Pause[3]", 1)] == expect
    assert actual[("Out_TDC_Stop", 2)] == expect
    cases["FH共通異常接点"] += 1

restart = rows("error")[18]
for allowed in (False, True):
    for pause in range(0, 9):
        values = {"In_Sw_START": allowed, "AutoMode": True, **{f"Pause[{i}]": pause == i for i in range(1, 9)}}
        actual = energized(restart, values)
        assert actual[("ST1_A_Ca1_M[6]", 5)] == (allowed and pause == 3)
        assert actual[("ST5_A_Ca2_M[6]", 6)] == (allowed and pause == 3)
        assert actual[("Pause[3]", 7)] == (allowed and pause == 3)
        cases["再開時の不一致解除接点"] += 1

report["delta_audit"] = {"limited_boolean_topology_cases": dict(cases), "physical_at_variables_unchanged": len(at_map(old)), "old_metadata_preserved": len(old_vars), "added_function_ids_unique": True}
b.REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report["delta_audit"], ensure_ascii=False, indent=2))
