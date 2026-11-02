"""B原本を保全し、左ST5カメラ2と既存処理への連動をC版へ追加する。"""
from pathlib import Path
import collections
import copy
import hashlib
import json
import re
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
INSPECTION = json.loads((BASE / "inspection.json").read_text(encoding="utf-8"))
SOURCE = Path(INSPECTION["source"])
DESTINATION = SOURCE.with_name(SOURCE.name.replace("20261026B", "20261026C"))
STAGED = BASE / DESTINATION.name
REPORT = BASE / "verification.json"
IDS = {
    "st1": "08c19951-3bae-402d-a637-be66c221f71b",
    "st5": "9d70f8e1-594f-4023-b6ae-7d63d464a215",
    "cv": "cc6ea326-2efd-437a-a0b6-6d1b9340d3f7",
    "fh": "fdce7b3c-0b49-4708-9024-8a98fe6b24b5",
    "output": "09c1f70b-b9ac-4e5d-884f-9779e69a597a",
    "error": "78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4",
    "globals": "f07dd06c-505c-431b-b9fc-098949805b4e",
    "movements_vars": "86df70c5-aaad-4d2c-bba7-04264d7b7f32",
    "other_vars": "a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10",
    "mode_vars": "b530d740-9d69-41c3-974a-97c06e823eb2",
    "io_vars": "9576fedf-9472-4ce6-b9ed-6eda5b4f0514",
    "metadata": "20a6b651-4c34-401a-965e-db3e18414d5c",
}
GLOBAL_PAIRS = {
    "ST1_A_Ca1_M": ("ST5_A_Ca2_M", "A(左側) ST5 カメラ2工程"),
    "ST1_A_Ca1_Busy": ("ST5_A_Ca2_Busy", "A(左側) ST5 カメラ2検査中"),
    "ST1_A_Ca1_End": ("ST5_A_Ca2_End", "A(左側) ST5 カメラ2動作完了"),
    "FH_5552_10_A_Auto": ("FH_A_ST5_Auto", "A(左側) ST5 FH自動測定"),
    "FH_A_ST1_Manual": ("FH_A_ST5_Manual", "A(左側) ST5 FH手動測定"),
    "FH_A_ST1_Done": ("FH_A_ST5_Done", "A(左側) ST5 画像検査完了"),
}
MESSAGE_MAP = {
    117: "A(左側) ST5 カメラ2 測定タイムアウト",
    118: "A(左側) ST5 カメラ2 OK",
    119: "A(左側) ST5 カメラ2 NG（結果0）",
    120: "A(左側) ST5 カメラ2 NG（結果1）",
    121: "A(左側) ST5 カメラ2 検査前ワーク不一致",
}


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def convert_string(text):
    for old, (new, _) in GLOBAL_PAIRS.items():
        text = text.replace(old, new)
    return (text.replace("FH_A_ST1_", "FH_A_ST5_")
            .replace("FH_Line0_", "FH_Line1_")
            .replace("Station_A_Data[1]", "Station_A_Data[5]")
            .replace("Pos_01_Stopper", "Pos_05_Stopper")
            .replace("Work_A_Pos_01", "Work_A_Pos_05")
            .replace("ST1", "ST5").replace("カメラ1", "カメラ2")
            .replace("位置1", "位置5").replace("Y720", "Y724"))


def converted(row, new_ids=False):
    result = copy.deepcopy(row)
    for node in walk(result):
        for key, value in list(node.items()):
            if isinstance(value, str):
                node[key] = str(uuid.uuid4()) if key == "Id" and new_ids else convert_string(value)
    return result


def set_xy_y(cell, y):
    if y:
        cell["Y"] = y
    else:
        cell.pop("Y", None)


def shape(row):
    """表示番号・GUID・コメントを除いた回路の厳密な配置/命令照合用。"""
    row = copy.deepcopy(row)
    row.pop("CMT", None)
    row.pop("LRI", None)
    row.pop("RRI", None)
    for node in walk(row):
        node.pop("Ix", None)
        node.pop("Id", None)
    for key in ("CLs", "VLs"):
        row[key] = sorted(row.get(key, []), key=lambda x: json.dumps(x, sort_keys=True))
    return row


def parse_decl(line):
    return dict(x.split("=", 1) for x in line[2:].split("\t") if "=" in x)


def declarations(text):
    return {parse_decl(line)["N"]: line for line in text.splitlines() if line.startswith("++D=")}


def decl_with(line, **changes):
    parts = line[2:].split("\t")
    for key, value in changes.items():
        present = next((i for i, x in enumerate(parts) if x.startswith(key + "=")), None)
        if present is None:
            parts.append(key + "=" + value)
        else:
            parts[present] = key + "=" + value
    return "++" + "\t".join(parts)


def ec_xml(values):
    return "<ECs>" + "".join('<EC EK="[%s]" C="%s" />' % (index, escape(value, {'"': '&quot;'})) for index, value in sorted(values.items())) + "</ECs>"


def add_decl(text, line, external=False):
    name = parse_decl(line)["N"]
    assert name not in declarations(text), name
    if external or "+GN=VAR_GLOBAL" in text:
        return text + line + "\r\n"
    marker = "+GN=VAR_EXTERNAL"
    assert text.count(marker) == 1
    return text.replace(marker, line + "\r\n" + marker, 1)


def native_indices_valid(row):
    """セル/引数のIxは一意、電源レールより前。配線Ixはレールより後。"""
    cells = [node for cell in row["CLs"] for node in walk(cell) if node.get("__type") in ("LD", "ST", "F", "FB", "PRM")]
    indices = [node.get("Ix", 0) for node in cells]
    assert len(indices) == len(set(indices)), (row.get("CMT"), indices)
    assert max(indices, default=-1) < row["LRI"] < row["RRI"]
    assert all(v["Ix"] > row["RRI"] for v in row.get("VLs", []))
    coords = [(c.get("X", 0), c.get("Y", 0)) for c in row["CLs"]]
    assert len(coords) == len(set(coords)), (row.get("CMT"), coords)


def build():
    assert not DESTINATION.exists(), "既存C版を上書きしません"
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == INSPECTION["source_sha256"], "調査後にB版が更新されました"
    with zipfile.ZipFile(SOURCE) as archive:
        assert archive.testzip() is None
        original = {n: archive.read(n) for n in archive.namelist()}
        infos, archive_comment = archive.infolist(), archive.comment
    texts = INSPECTION["texts"]
    names = {key: next(n for n in texts if n.endswith(value + ".xml")) for key, value in IDS.items()}
    changes = {}
    ladder_counts = {}
    for name, text in texts.items():
        if text.lstrip().startswith("{"):
            try:
                rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            except json.JSONDecodeError:
                continue
            if rows and all(isinstance(r, dict) and "CLs" in r for r in rows):
                ladder_counts[name] = len(rows)

    def rows_for(key):
        return [json.loads(line) for line in texts[names[key]].splitlines() if line.strip()]

    changed_rungs = {}

    def replace_rows(key, replacements=None, append=None):
        name = names[key]
        lines = texts[name].splitlines(keepends=True)
        assert len(lines) == ladder_counts[name]
        for index, row in (replacements or {}).items():
            native_indices_valid(row)
            ending = "\r\n" if lines[index].endswith("\r\n") else "\n"
            lines[index] = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + ending
        if append:
            for row in append:
                native_indices_valid(row)
            ending = "\r\n" if "\r\n" in texts[name] else "\n"
            assert lines[-1].endswith(ending)
            lines.extend(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + ending for row in append)
        changes[name] = "".join(lines)
        changed_rungs[key] = {"replaced": sorted((replacements or {}).keys()), "appended": len(append or [])}
        ladder_counts[name] = len(lines)

    # 追加済みコピーの６行をそのまま生かし、関連信号・位置・コメントをST5へ分離する。
    st1_rows, st5_rows = rows_for("st1"), rows_for("st5")
    assert len(st1_rows) == len(st5_rows) == 6
    assert [shape(r) for r in st1_rows] == [shape(r) for r in st5_rows]
    new_st5 = [converted(row) for row in st5_rows]
    st5_titles = ["検査開始", "検査中", "位置5ストッパー戻", "ワーク有無判定", "測定開始", "動作完了"]
    for i, row in enumerate(new_st5):
        row["CMT"] = "A(左側) ST5 カメラ2 " + st5_titles[i]
    replace_rows("st5", dict(enumerate(new_st5)))
    assert not any(old in changes[names["st5"]] for old in ("ST1_A_Ca1", "FH_A_ST1", "FH_5552_10_A_Auto", "Pos_01", "Station_A_Data[1]"))

    # メーカーI/O割付コメントでST5に対応するLine1へ、ST1と同じ８行を追加する。
    fh_rows = rows_for("fh")
    assert len(fh_rows) == 8
    new_fh = [converted(row, new_ids=True) for row in fh_rows]
    message_replacements = {113: 118, 114: 119, 115: 120}
    fh_titles = ["測定要求", "シーン切替（ON=0／OFF=1）", "コマンド完了", "トリガー出力（100ms）", "測定完了", "OK判定", "NG判定", "検査完了"]
    for i, row in enumerate(new_fh):
        row["CMT"] = "A(左側) ST5 カメラ2 " + fh_titles[i]
        for node in walk(row):
            if node.get("Var") in {f"INT#{i}" for i in message_replacements}:
                node["Var"] = "INT#" + str(message_replacements[int(node["Var"].split("#")[1])])
    replace_rows("fh", append=new_fh)

    # コンベア移動前の全工程完了条件へST5の完了接点を直列追加する。
    cv = rows_for("cv")[0]
    assert cv["LRI"] == 10
    for cell in cv["CLs"]:
        if cell.get("X", 0) >= 5:
            cell["X"] += 1
    cv["CLs"].extend([
        {"__type": "LD", "Ix": 10, "Var": "ST5_A_Ca2_End", "X": 5},
        {"__type": "HL", "X": 5, "Y": 1},
    ])
    cv["LRI"] += 1
    cv["RRI"] += 1
    for wire in cv.get("VLs", []):
        wire["Ix"] += 1
        if wire.get("X", 0) >= 5:
            wire["X"] += 1
    replace_rows("cv", {0: cv})

    # 位置５の既存出力へ[2]を並列追加。右側の並列コイル位置は動かさない。
    output_rows = rows_for("output")
    output = copy.deepcopy(output_rows[136])
    assert output["LRI"] == 13
    for cell in output["CLs"]:
        if cell.get("X", 0) < 4 and cell.get("Y", 0) >= 1:
            cell["Y"] += 1
    for wire in output["VLs"]:
        wire["Ix"] += 1
        if wire.get("X", 0) == 4 and wire.get("Y", 0) >= 1:
            wire["Y"] += 1
    output["CLs"].append({"__type": "LD", "Ix": 13, "Var": "Out_CYS_Pos_05_Stopper_A_H_Auto[2]", "Y": 1})
    output["LRI"] += 1
    output["RRI"] += 1
    output["VLs"].extend([{"Ix": 16, "X": 4, "Y": 1}, {"Ix": 18, "X": 1}])
    template = converted(output_rows[112])
    for node in walk(template):
        if isinstance(node.get("Var"), str):
            node["Var"] = node["Var"].replace("Output_A_M[27]", "Output_A_M[35]").replace("Output_A_Reset_TON[27]", "Output_A_Reset_TON[35]")
    assert shape(template) == shape(output), "位置１の既存出力と位置５の回路形状が違います"
    assert shape(converted(output_rows[113])) != shape(output_rows[137])  # 内部保持番号は台別
    replace_rows("output", {136: output})

    # FH共通停止ラダーにST5専用タイマーとワーク不一致を追加。停止コイルは増やさない。
    error_rows = rows_for("error")
    err = copy.deepcopy(error_rows[11])
    assert err["LRI"] == 32
    for cell in err["CLs"]:
        if cell.get("X", 0) < 3 and cell.get("Y", 0) >= 6:
            cell["Y"] += 2
    next_index = 32

    def new_cell(old, x, y):
        nonlocal next_index
        result = copy.deepcopy(old)
        result["X"] = x
        set_xy_y(result, y)
        for node in walk(result):
            if "Ix" in node or node is result:
                node["Ix"] = next_index
                next_index += 1
            if "Id" in node:
                node["Id"] = str(uuid.uuid4())
        return result

    timeout = [new_cell(error_rows[11]["CLs"][i], i, 6) for i in (0, 1, 2)]
    timeout[0]["Var"] = "FH_A_ST5_Auto"
    timeout[1]["Var"] = "Error_TON[4]"
    timeout[2]["In"][1]["Var"] = "INT#117"
    mismatch = [new_cell(next(c for c in error_rows[11]["CLs"] if c.get("Var") == "ST1_A_Ca1_M[6]"), 0, 7),
                new_cell(next(c for c in error_rows[11]["CLs"] if c.get("Name") == "MOVE" and c.get("Y") == 5), 1, 7)]
    mismatch[0]["Var"] = "ST5_A_Ca2_M[6]"
    mismatch[1]["In"][1]["Var"] = "INT#121"
    assert next_index == 43
    err["CLs"].extend(timeout + mismatch + [{"__type": "HL", "X": 2, "Y": 7}])
    err["LRI"] += 11
    err["RRI"] += 11
    for wire in err["VLs"]:
        wire["Ix"] += 11
    err["VLs"].extend([{"Ix": 45, "X": 3, "Y": 6}, {"Ix": 45, "X": 3, "Y": 7}])
    err["CMT"] += "\r\nA(左側) ST1/ST5 共通停止・ST5測定10秒監視"
    assert [c for c in err["CLs"] if c["__type"] == "ST"] == [c for c in error_rows[11]["CLs"] if c["__type"] == "ST"]

    # 再開条件と非常停止接点は保持し、同じPause[3]分岐へST5の不一致解除を追加する。
    restart = copy.deepcopy(error_rows[18])
    assert restart["LRI"] == 44
    for cell in restart["CLs"]:
        if cell.get("X", 0) >= 19 and cell.get("Y", 0) >= 6:
            cell["Y"] += 1
    for wire in restart["VLs"]:
        wire["Ix"] += 1
        if wire.get("X", 0) >= 19 and wire.get("Y", 0) >= 6:
            wire["Y"] += 1
    restart["CLs"].append({"__type": "ST", "Ix": 44, "RS": True, "Var": "ST5_A_Ca2_M[6]", "X": 20, "Y": 6})
    restart["LRI"] += 1
    restart["RRI"] += 1
    restart["VLs"].extend([{"Ix": 50, "X": 20, "Y": 6}, {"Ix": 48, "X": 19, "Y": 6}])
    assert [c for c in restart["CLs"] if c.get("X", 0) < 19] == [c for c in error_rows[18]["CLs"] if c.get("X", 0) < 19]
    replace_rows("error", {11: err, 18: restart})

    # 新規実体変数６個を登録し、使用する各プログラムの外部参照も同じ型で登録する。
    global_text = texts[names["globals"]]
    old_globals = declarations(global_text)
    new_globals = {}
    for old, (new, comment) in GLOBAL_PAIRS.items():
        line = decl_with(convert_string(old_globals[old]), N=new, Com=comment)
        if new == "ST5_A_Ca2_M":
            ec = {
                1: "A(左側) ST5 カメラ2検査開始", 2: "【Y724】A(左側) ST5 ストッパー戻",
                3: "A(左側) ST5 ワーク有無判定", 4: "A(左側) ST5 ワーク有",
                5: "A(左側) ST5 ワーク無", 6: "A(左側) ST5 検査前ワーク不一致",
                7: "A(左側) ST5 FH測定開始",
            }
            line = decl_with(line, EC=ec_xml(ec))
        global_text = add_decl(global_text, line)
        new_globals[new] = line
    changes[names["globals"]] = global_text
    new_all_globals = declarations(global_text)
    added_declarations = {"globals": list(new_globals)}

    scopes = {
        "movements_vars": ["ST5_A_Ca2_M", "ST5_A_Ca2_Busy", "ST5_A_Ca2_End", "FH_A_ST5_Auto", "FH_A_ST5_Done", "Out_CYS_Pos_05_Stopper_A_H_Done"],
        "other_vars": ["FH_A_ST5_Auto", "FH_A_ST5_Manual", "FH_A_ST5_Done"],
        "mode_vars": ["ST5_A_Ca2_M", "FH_A_ST5_Auto"],
    }
    for key, required in scopes.items():
        text = texts[names[key]]
        added_declarations[key] = []
        if key == "other_vars":
            for old in ["FH_A_ST1_M", "FH_A_ST1_OK", "FH_A_ST1_NG", "FH_A_ST1_TON", "FH_A_ST1_TOF"]:
                line = convert_string(declarations(text)[old])
                line = decl_with(line, Com={
                    "FH_A_ST1_M": "A(左側) ST5 FH工程", "FH_A_ST1_OK": "A(左側) ST5 OK判定",
                    "FH_A_ST1_NG": "A(左側) ST5 NG判定", "FH_A_ST1_TON": "A(左側) ST5 FH遅延タイマー",
                    "FH_A_ST1_TOF": "A(左側) ST5 FHトリガ保持",
                }[old])
                if old == "FH_A_ST1_M":
                    line = decl_with(line, EC=ec_xml({
                        1: "A(左側) ST5 測定要求", 2: "A(左側) ST5 シーン切替",
                        3: "A(左側) ST5 コマンド完了", 4: "A(左側) ST5 測定トリガー",
                        5: "A(左側) ST5 測定完了", 6: "A(左側) ST5 OK保持", 7: "A(左側) ST5 NG／完了保持",
                    }))
                elif old == "FH_A_ST1_TOF":
                    line = decl_with(line, EC=ec_xml({1: "A(左側) ST5 トリガー100ms"}))
                text = add_decl(text, line)
                added_declarations[key].append(parse_decl(line)["N"])
            # 実割付Line1の各使用信号を外部参照へ追加（既存なら型一致だけを確認）。
            required += sorted({n["Var"].split("[")[0].split(".")[0] for r in new_fh for n in walk(r)
                                if isinstance(n.get("Var"), str) and n["Var"].startswith("FH_Line1_")})
        for name in required:
            if name in declarations(text):
                assert parse_decl(declarations(text)[name])["D"] == parse_decl(new_all_globals[name])["D"]
                continue
            # 外部変数はグローバル実体の参照。物理ATは複写しない。
            external_line = decl_with(new_all_globals[name], G="VAR_EXTERNAL")
            external_line = re.sub(r"\tAT=[^\t\r\n]*", "", external_line)
            text = add_decl(text, external_line, external=True)
            added_declarations[key].append(name)
        if key == "mode_vars":
            old_line = declarations(text)["Error_TON"]
            assert not any(re.search(r'(?<![A-Za-z0-9_])Error_TON\[4\]', t) for n, t in texts.items() if n in ladder_counts)
            text = text.replace(old_line, decl_with(old_line, EC=ec_xml({4: "A(左側) ST5 Ca2測定タイムアウト"})), 1)
        changes[names[key]] = text

    # 位置５ストッパー要求の用途コメントをグローバル／参照宣言へ追加する。
    for key in ("globals", "movements_vars", "io_vars"):
        name = names[key]
        text = changes.get(name, texts[name])
        line = declarations(text)["Out_CYS_Pos_05_Stopper_A_H_Auto"]
        parsed = parse_decl(line)
        ec = {int(e.get("EK").strip("[]")): e.get("C") for e in ET.fromstring(parsed.get("EC", "<ECs/>"))}
        assert 2 not in ec
        ec[2] = "A(左側) ST5 カメラ2検査開始"
        changes[name] = text.replace(line, decl_with(line, EC=ec_xml(ec)), 1)

    # HMI連携用の変数メタ情報だけ登録。画面本文や警報メッセージは編集しない。
    meta_name = names["metadata"]
    meta = texts[meta_name]
    new_nodes = []
    for old, (new, comment) in GLOBAL_PAIRS.items():
        matches = list(re.finditer(r'<Variable\s[^<>]*\bName="' + re.escape(old) + r'"[^<>]*/>', meta))
        assert len(matches) == 1, old
        node = ET.fromstring(matches[0][0])
        node.set("Name", new)
        node.set("Address", "new_Controller_0." + new)
        node.set("Comment", comment)
        node.set("Id", str(uuid.uuid4()))
        new_nodes.append(ET.tostring(node, encoding="unicode", short_empty_elements=True))
    marker = "  </VariableGroup>"
    assert marker in meta
    meta = meta.replace(marker, "".join("    " + node + "\r\r\n" for node in new_nodes) + marker, 1)
    changes[meta_name] = meta
    ET.fromstring(meta)

    # 新規ラダー参照が実体変数／ローカル／外部参照のいずれかで宣言済みか確認する。
    scope_map = {"st5": "movements_vars", "cv": "movements_vars", "fh": "other_vars", "error": "mode_vars", "output": "io_vars"}
    for key, scope in scope_map.items():
        table = declarations(changes.get(names[scope], texts[names[scope]]))
        for row in [json.loads(s) for s in changes[names[key]].splitlines() if s.strip()]:
            for node in walk(row):
                value = node.get("Var", "")
                if not value or value in ("TRUE", "FALSE", "P_On", "P_Off") or not re.match(r"^[A-Za-z_]", value) or "#" in value:
                    continue
                root = re.split(r"[.\[]", value, maxsplit=1)[0]
                assert root in table, (key, root)
    # 元の各宣言にある型・割付・保持属性は一切変更しない。宣言行の追加とECだけ。
    for key in ("globals", "movements_vars", "other_vars", "mode_vars", "io_vars"):
        old_table = declarations(texts[names[key]])
        new_table = declarations(changes[names[key]])
        assert len(new_table) == len([l for l in changes[names[key]].splitlines() if l.startswith("++D=")])
        for name, line in old_table.items():
            a, b = parse_decl(line), parse_decl(new_table[name])
            a.pop("EC", None)
            b.pop("EC", None)
            assert a == b, (key, name)
        for name, line in new_table.items():
            d = parse_decl(line)
            if d["G"] == "VAR_EXTERNAL":
                assert d["D"] == parse_decl(declarations(changes[names["globals"]])[name])["D"], (key, name)
                if name not in old_table:
                    assert "AT" not in d, "新規外部参照へ物理ATを複写してはいけません"

    # 元のST1、出力セクションの他315行、FHの元８行、その他のZIPは完全に保持。
    assert names["st1"] not in changes
    assert changes[names["fh"]].startswith(texts[names["fh"]])
    for key, changed in [("output", {136}), ("cv", {0}), ("error", {11, 18})]:
        old_lines = texts[names[key]].splitlines()
        new_lines = changes[names[key]].splitlines()
        assert len(old_lines) == len(new_lines)
        assert all(a == b for i, (a, b) in enumerate(zip(old_lines, new_lines)) if i not in changed)
    assert all(not n.endswith(".dat") for n in changes)
    assert len(changes) == 11, list(changes)
    for name in ladder_counts:
        if name in changes:
            for row in (json.loads(line) for line in changes[name].splitlines() if line.strip()):
                # 既存の他行はネイティブ変換で検証する。独自Ix制約を既存行へ強要しない。
                assert "CLs" in row and "LRI" in row and "RRI" in row
    with zipfile.ZipFile(STAGED, "w") as archive:
        archive.comment = archive_comment
        for info in infos:
            raw = original[info.filename]
            if info.filename in changes:
                raw = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + changes[info.filename].encode("utf-8")
            archive.writestr(info, raw)
    with zipfile.ZipFile(STAGED) as archive:
        assert archive.testzip() is None and archive.namelist() == list(original)
        assert all(archive.read(n) == data for n, data in original.items() if n not in changes)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == INSPECTION["source_sha256"]
    report = {
        "source": str(SOURCE), "destination": str(DESTINATION), "staged": str(STAGED),
        "source_sha256": INSPECTION["source_sha256"], "output_sha256": hashlib.sha256(STAGED.read_bytes()).hexdigest(),
        "entries": len(original), "changed_entries": list(changes), "changed_rungs": changed_rungs,
        "added_declarations": added_declarations, "new_hmi_message_numbers_require_screen_registration": MESSAGE_MAP,
        "ladder_counts": ladder_counts, "native_validation": None,
        "st1_preserved": True, "physical_io_assignments_unchanged": True,
        "app_build_verified": False, "machine_transfer_performed": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("ladder_counts", "native_validation")}, ensure_ascii=False, indent=2))


def publish():
    report = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    assert report["native_validation"] and all("PARSE_FAIL=0 MODEL_FAIL=0" in v for v in report["native_validation"].values())
    assert report.get("delta_audit", {}).get("physical_at_variables_unchanged") == 722
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report["source_sha256"]
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest() == report["output_sha256"]
    with STAGED.open("rb") as incoming, DESTINATION.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    note = [
        "左ST5 カメラ2検査の展開（20261026B → C）",
        "B原本保全。コピー元ST1のラダーと変数はそのまま保持。",
        "ST5本体：ST5_A_Ca2_M／Busy／End、位置5ワーク／ストッパー／Station_A_Data[5]へ変更。",
        "カメラ：既存割付コメントのA(左側)ST5に対応するFH_Line1_*_1を使用。",
        "FH_A_ST5_Auto／Manual／Doneを追加。FH_5552_10末尾にST5測定ラダー8行を追加。",
        "コンベアの全ST完了条件にST5_A_Ca2_Endを追加。",
        "Output_出力：位置5ストッパー戻要求[2]を既存[1]へ並列追加。その他315行は保持。",
        "Error_エラー処理：既存FH停止Pause[3]にST5測定タイムアウト10秒とワーク不一致を追加。",
        "再開時の同一Pause[3]分岐へST5のワーク不一致M[6]リセットを追加。既存停止・再開条件は保持。",
        "実体グローバル6個、FHローカル5個、必要な外部変数参照を追加。コメントもST5へ対応。",
        "既存のEtherCAT設定・I/OのATアドレス・安全接点は変更なし。",
        "",
        "【HMIの表示文登録が必要：PLC側に追加した未使用番号】",
    ]
    note += [f"{number}：{message}" for number, message in MESSAGE_MAP.items()]
    note += [
        "画面のメッセージ本文や手動操作ボタンは未追加。既存HMI_MessageNo[0]を共用するため、同時事象時は後段の代入が優先（コピー元と同じ）。",
        "",
        "【使用前の確認】",
        "FHのシーン指令0/1、結果0/1の±1000判定、10秒監視、100msトリガーはST1の値を踏襲。ST5の実カメラ設定との適合は未確認。",
        "コピー元にあるFH工程M[7]の複数コイルなど、既存の基本ロジックは改造せず踏襲。",
        f"ZIP検証と同梱のラダー読込み変換検証：{len(report['ladder_counts'])}セクション、{sum(report['ladder_counts'].values())}行。",
        "Sysmac画面での全体ビルド／シミュレーター／実機動作は未確認。PLC接続・転送は実施していません。",
        "C版をオフラインで読み込み、全体ビルドとST5の順序・カメラ設定・表示メッセージを確認してから使用してください。",
    ]
    DESTINATION.with_suffix(".変更内容.txt").write_text("\n".join(note) + "\n", encoding="utf-8-sig")
    assert hashlib.sha256(DESTINATION.read_bytes()).hexdigest() == report["output_sha256"]
    print("保存完了", DESTINATION)


if __name__ == "__main__":
    publish() if "--publish" in sys.argv else build()
