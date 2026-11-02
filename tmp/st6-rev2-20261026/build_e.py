"""承認済み３点を修正し、左ST6反転2と既存連動処理をE版へ展開する。"""
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
DATA = json.loads((BASE / "inspection.json").read_text(encoding="utf-8"))
SOURCE = Path(DATA["source"])
DESTINATION = SOURCE.with_name(SOURCE.name.replace("20261026D", "20261026E"))
STAGED = BASE / DESTINATION.name
REPORT = BASE / "verification.json"
IDS = {
    "st4": "4a05531b-6bae-4cd7-9d4d-e3d6f875d1dc.xml",
    "st6": "a21ed85c-6215-4d9f-82fa-9123c6fd7db3.xml",
    "cv": "cc6ea326-2efd-437a-a0b6-6d1b9340d3f7.xml",
    "motion": "4bc99ae0-7ace-4891-a17a-c3fe2079278d.xml",
    "error": "78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml",
    "output": "09c1f70b-b9ac-4e5d-884f-9779e69a597a.xml",
    "globals": "f07dd06c-505c-431b-b9fc-098949805b4e.xml",
    "movements_vars": "86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml",
    "other_vars": "a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml",
    "mode_vars": "b530d740-9d69-41c3-974a-97c06e823eb2.xml",
    "io_vars": "9576fedf-9472-4ce6-b9ed-6eda5b4f0514.xml",
    "metadata": "20a6b651-4c34-401a-965e-db3e18414d5c.xml",
}
GLOBAL_PAIRS = {
    "ST4_A_Rev1_M": ("ST6_A_Rev2_M", "A(左側) ST6 反転2工程"),
    "Stm_A_Rev_Axis000_MovePos_Degree": ("Stm_A_Rev_Axis001_MovePos_Degree", "A(左側) ST6 反転2指令角度"),
    "Stm_A_Rev_Axis000_MoveAbsoluteDone": ("Stm_A_Rev_Axis001_MoveAbsoluteDone", "A(左側) ST6 反転2位置決め完了"),
    "HMI_Stm_A_Rev_Axis000_MovePos_Degree": ("HMI_Stm_A_Rev_Axis001_MovePos_Degree", "A(左側) ST6 反転2設定角度"),
    "Stm_A_Rev_Axis000_Auto": ("Stm_A_Rev_Axis001_Auto", "A(左側) ST6 反転2自動指令"),
    "Homing_Para_Stm": ("Homing_Para_Stm_Rev2", "A(左側) ST6 反転2原点設定"),
}
ST6_EC = {
    1: "動作開始", 2: "【Y714】ピックアップ戻", 3: "【Y725】位置6ストッパー戻",
    4: "原点角度転送", 5: "原点位置移動開始", 6: "原点位置移動完了", 7: "ワーク有無判定",
    8: "ワーク有・前工程OK", 9: "ワーク無・前工程NG", 10: "ワーク不一致エラー",
    11: "【Y715】反転前ピックアップ行", 12: "【Y712】チャック閉", 13: "【Y714】反転前ピックアップ戻",
    14: "反転角度転送", 15: "反転位置移動完了", 16: "【Y715】設置ピックアップ行",
    17: "【Y713】チャック開", 18: "【Y714】設置ピックアップ戻",
}


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def convert(value):
    return (value.replace("ST4_A_Rev1", "ST6_A_Rev2").replace("ST4_A_Rev_End", "ST6_A_Rev2_End")
            .replace("Stm_A_Rev_Axis000", "Stm_A_Rev_Axis001").replace("Homing_Para_Stm", "Homing_Para_Stm_Rev2")
            .replace("Rev_01_", "Rev_02_").replace("Pos_04_Stopper", "Pos_06_Stopper")
            .replace("Work_A_Pos_04", "Work_A_Pos_06").replace("Station_A_Data[4]", "Station_A_Data[6]")
            .replace("Pause[8]", "Pause[12]").replace("Error_M[8]", "Error_M[12]"))


def mapped(row):
    row = copy.deepcopy(row)
    for node in walk(row):
        for key, value in list(node.items()):
            if isinstance(value, str) and key in ("Var", "TXT"):
                node[key] = convert(value)
    return row


def shape(row):
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


def normalize(row, fresh_ids=False):
    index = 0
    for cell in row["CLs"]:
        for node in walk(cell):
            if node.get("__type") in ("LD", "ST", "F", "FB", "PRM"):
                node["Ix"] = index
                index += 1
            if fresh_ids and "Id" in node:
                node["Id"] = str(uuid.uuid4())
    row["LRI"], row["RRI"] = index, index + 1
    wire_ids = {}
    for wire in row.get("VLs", []):
        if wire["Ix"] not in wire_ids:
            wire_ids[wire["Ix"]] = index + 2 + len(wire_ids)
        wire["Ix"] = wire_ids[wire["Ix"]]
    coords = [(c.get("X", 0), c.get("Y", 0)) for c in row["CLs"]]
    assert len(coords) == len(set(coords)), row.get("CMT")
    return row


def declarations(text):
    return {parse_decl(l)["N"]: l for l in text.splitlines() if l.startswith("++D=")}


def parse_decl(line):
    return dict(p.split("=", 1) for p in line[2:].split("\t") if "=" in p)


def with_fields(line, **fields):
    parts = line[2:].split("\t")
    for key, value in fields.items():
        i = next((i for i, p in enumerate(parts) if p.startswith(key + "=")), None)
        if i is None:
            parts.append(key + "=" + value)
        else:
            parts[i] = key + "=" + value
    return "++" + "\t".join(parts)


def ec_xml(values):
    return "<ECs>" + "".join('<EC EK="[%s]" C="%s" />' % (i, escape(c, {'"': '&quot;'})) for i, c in sorted(values.items())) + "</ECs>"


def add_decl(text, line, external=False):
    assert parse_decl(line)["N"].lower() not in {n.lower() for n in declarations(text)}
    if external or "+GN=VAR_GLOBAL" in text:
        return text + line + "\r\n"
    marker = "+GN=VAR_EXTERNAL"
    assert text.count(marker) == 1
    return text.replace(marker, line + "\r\n" + marker, 1)


def parallel_auto2(row, var):
    row = copy.deepcopy(row)
    assert any(c.get("Var") == var + "[1]" for c in row["CLs"])
    # 入力側だけを１行下げる。右側並列コイルを動かしてはいけない。
    for cell in row["CLs"]:
        if cell.get("X", 0) < 4 and cell.get("Y", 0) >= 1:
            cell["Y"] += 1
    for wire in row["VLs"]:
        if wire.get("X") == 4 and wire.get("Y", 0) >= 1:
            wire["Y"] += 1
    merge_id = next(w["Ix"] for w in row["VLs"] if w["X"] == 4)
    fresh_id = max(w["Ix"] for w in row["VLs"]) + 1
    row["CLs"].append({"__type": "LD", "Var": var + "[2]", "Y": 1})
    row["VLs"].extend([{"Ix": merge_id, "X": 4, "Y": 1}, {"Ix": fresh_id, "X": 1}])
    return normalize(row)


def build():
    assert not DESTINATION.exists(), "既存E版を上書きしません"
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == DATA["source_sha256"], "調査後にD版が更新されました"
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original = {n: z.read(n) for n in z.namelist()}
        infos, archive_comment = z.infolist(), z.comment
    texts = DATA["texts"]
    names = {k: next(n for n in texts if n.endswith(v)) for k, v in IDS.items()}
    original_ladders = {}
    for n, t in texts.items():
        if not t.lstrip().startswith("{"):
            continue
        try:
            rows = [json.loads(l) for l in t.splitlines() if l.strip()]
        except json.JSONDecodeError:
            continue
        if rows and all(isinstance(r, dict) and "CLs" in r for r in rows):
            original_ladders[n] = rows
    changes, additions, edited_rows = {}, {}, {}

    def save_rows(key, replacements=None, append=None, insert_before=None):
        name = names[key]
        lines = texts[name].splitlines(keepends=True)
        assert len(lines) == len(original_ladders[name])
        ending = "\r\n" if "\r\n" in texts[name] else "\n"
        for i, row in (replacements or {}).items():
            lines[i] = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + ending
        if insert_before:
            i, rows = insert_before
            lines[i:i] = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) + ending for r in rows]
        if append:
            lines += [json.dumps(r, ensure_ascii=False, separators=(",", ":")) + ending for r in append]
        changes[name] = "".join(lines)
        edited_rows[key] = {"changed_original_rows": sorted((replacements or {}).keys()), "added": len(append or []) + (len(insert_before[1]) if insert_before else 0)}

    # 承認①：ST4のチャック閉/完了を反転１へ戻す。
    st4 = copy.deepcopy(original_ladders[names["st4"]])
    st6_source = original_ladders[names["st6"]]
    assert len(st4) == len(st6_source) == 17
    assert [shape(r) for r in st4] == [shape(r) for r in st6_source]
    for i in (9, 10):
        for node in walk(st4[i]):
            if isinstance(node.get("Var"), str):
                node["Var"] = node["Var"].replace("Out_CYw_Rev_02_Chk_A_H", "Out_CYw_Rev_01_Chk_A_H")
    st4[9]["CMT"] = "A(左側) ST4 反転1 【Y708】チャック閉"
    # 承認③：不一致出力を通常コイルへ変更。
    coil = next(c for c in st4[7]["CLs"] if c.get("__type") == "ST" and c.get("Var") == "ST4_A_Rev1_M[10]")
    assert coil.pop("RS") is True
    save_rows("st4", {7: st4[7], 9: st4[9], 10: st4[10]})

    # 追加済みST6の形状/GUIDを生かして、承認した同じ３点とST6向け参照に対応させる。
    st6 = [mapped(r) for r in st6_source]
    for row in st6:
        for c in row["CLs"]:
            if c.get("Var") == "ST6_A_Rev2_M[10]" and c.get("__type") == "ST":
                c.pop("RS", None)
    titles = ["動作開始", "動作中", "【Y714】ピックアップ戻", "【Y725】位置6ストッパー戻", "原点角度転送", "原点位置移動開始", "原点位置移動完了", "ワーク有無・不一致判定", "【Y715】反転前ピックアップ行", "【Y712】チャック閉", "【Y714】反転前ピックアップ戻", "反転角度転送", "反転位置移動完了", "【Y715】設置ピックアップ行", "【Y713】チャック開", "【Y714】設置ピックアップ戻", "動作完了"]
    for row, title in zip(st6, titles):
        row["CMT"] = "A(左側) ST6 反転2 " + title
    save_rows("st6", dict(enumerate(st6)))
    assert not any(x in changes[names["st6"]] for x in ("ST4_A_Rev", "Axis000", "Rev_01_", "Pos_04", "Station_A_Data[4]", "Pause[8]"))

    # 位置６ストッパー、反転２ピックアップの設置側要求[2]も既存出力へ追加。
    outputs = original_ladders[names["output"]]
    out_replacements = {
        94: parallel_auto2(outputs[94], "Out_CYw_Rev_02_Pick_A_H_Auto"),
        97: parallel_auto2(outputs[97], "Out_CYw_Rev_02_Pick_A_F_Auto"),
        142: parallel_auto2(outputs[142], "Out_CYS_Pos_06_Stopper_A_H_Auto"),
    }
    for source_i, target_i, old_no, new_no in [(82, 94, 17, 21), (85, 97, 18, 22), (130, 142, 33, 37)]:
        expected = mapped(outputs[source_i])
        for node in walk(expected):
            if isinstance(node.get("Var"), str):
                node["Var"] = node["Var"].replace(f"Output_A_M[{old_no}]", f"Output_A_M[{new_no}]").replace(f"Output_A_Reset_TON[{old_no}]", f"Output_A_Reset_TON[{new_no}]").replace("Mtr_Flip_01_Busy", "Mtr_Flip_02_Busy")
        assert shape(expected) == shape(out_replacements[target_i]), target_i
    save_rows("output", out_replacements)
    # 既存のST6仮完了接点だけを、新しいST6の完了へ置換する。
    cv = copy.deepcopy(original_ladders[names["cv"]][0])
    assert sum(c.get("Var") == "ST6_Ins_Cv_Rdy" for c in cv["CLs"]) == 1
    for cell in cv["CLs"]:
        if cell.get("Var") == "ST6_Ins_Cv_Rdy":
            cell["Var"] = "ST6_A_Rev2_End"
    save_rows("cv", {0: cv})

    # 承認②：ST4の不一致判定をM[10]へ。ST6専用Error/Pause[12]も追加。
    assert not any(re.fullmatch(r"(?:Pause|Error_M)\[12\]", n.get("Var", "")) for rows in original_ladders.values() for row in rows for n in walk(row))
    errors = original_ladders[names["error"]]
    st4_error = copy.deepcopy(errors[20])
    assert st4_error["CLs"][0]["Var"] == "ST4_A_Rev1_M[9]"
    st4_error["CLs"][0]["Var"] = "ST4_A_Rev1_M[10]"
    st4_error["CMT"] = "A(左側) ST4 反転1 ワーク不一致エラー"
    st6_error = mapped(st4_error)
    st6_error["CMT"] = "A(左側) ST6 反転2 ワーク不一致エラー"
    # 既存の再開回路の左条件・並列枝を保持し、新エラー接点とPause[12]解除枝だけ追加。
    restart = copy.deepcopy(errors[-1])
    assert restart["CLs"][0]["Var"] == "In_Sw_START"
    left_before = [copy.deepcopy(c) for c in restart["CLs"] if c.get("X", 0) < 22]
    for c in restart["CLs"]:
        if c.get("X", 0) >= 21:
            c["X"] += 1
    for wire in restart["VLs"]:
        if wire.get("X", 0) >= 21:
            wire["X"] += 1
    restart["CLs"] += [
        {"__type": "LD", "Not": True, "Var": "Error_M[12]", "X": 21},
        {"__type": "LD", "Var": "Pause[12]", "X": 23, "Y": 24},
        {"__type": "ST", "RS": True, "Var": "Out_TDC_Stop", "X": 24, "Y": 24},
        {"__type": "ST", "RS": True, "Var": "Pause[12]", "X": 24, "Y": 25},
    ]
    common_wire = next(w["Ix"] for w in restart["VLs"] if w["X"] == 23)
    fresh_wire = max(w["Ix"] for w in restart["VLs"]) + 1
    restart["VLs"] += [{"Ix": common_wire, "X": 23, "Y": y} for y in (22, 23)] + [{"Ix": fresh_wire, "X": 24, "Y": 24}]
    normalize(restart)
    assert [{k: v for k, v in c.items() if k not in ("X", "Y", "Ix")} for c in left_before] == [{k: v for k, v in c.items() if k not in ("X", "Y", "Ix")} for c in restart["CLs"] if c.get("X", 0) < 23 and c.get("Var") != "Error_M[12]"]
    save_rows("error", {20: st4_error, len(errors) - 1: restart}, insert_before=(21, [st6_error]))

    # 反転２のモータ処理を、既存Axis001へ専用FB/パラメータで追加する。機器設定は不変。
    motion_old = original_ladders[names["motion"]]
    assert len(motion_old) == 4
    motion_new = [mapped(r) for r in motion_old]
    motion_titles = ["電源ON", "原点・動作パラメータ", "原点復帰完了", "絶対位置決め"]
    inline_eid, inline_entity_id = str(uuid.uuid4()), str(uuid.uuid4())
    inline = next(c for c in motion_new[1]["CLs"] if c["__type"] == "IST")
    old_eid = inline["EID"]
    inline["EID"] = inline_eid
    for row, title in zip(motion_new, motion_titles):
        row["CMT"] = "A(左側) ST6 反転2 " + title
        for node in walk(row):
            if "Id" in node:
                node["Id"] = str(uuid.uuid4())
    save_rows("motion", append=motion_new)
    # インラインSTのOEM登録は名前/追跡IDをラダーEIDと一致させる。
    oem_name = DATA["oem_name"]
    oem = texts[oem_name]
    matches = list(re.finditer(r'<Entity\b[^>]*type="Inline"[^>]*name="' + re.escape(old_eid) + r'"[^>]*>.*?</Entity>', oem, re.DOTALL))
    assert len(matches) == 1
    old_inline_xml = matches[0][0]
    old_inline_entity = ET.fromstring(old_inline_xml)
    old_inline_entity_id = old_inline_entity.get("id")
    new_inline_xml = old_inline_xml.replace(old_inline_entity_id, inline_entity_id).replace(old_eid, inline_eid)
    changes[oem_name] = oem[:matches[0].end()] + "\r\r\n                          " + new_inline_xml + oem[matches[0].end():]
    prefix = names["motion"].rsplit("/", 1)[0] + "/"
    bookmark_template = prefix + old_inline_entity_id + ".BookmarkGroup"
    assert bookmark_template in original
    additions[prefix + inline_entity_id + ".BookmarkGroup"] = original[bookmark_template]

    # 実体グローバル６個。Busy/Endはコピー元同様Movementsローカルのままにする。
    table = texts[names["globals"]]
    global_old = declarations(table)
    for old, (new, comment) in GLOBAL_PAIRS.items():
        line = with_fields(global_old[old], N=new, Com=comment)
        if new == "ST6_A_Rev2_M":
            line = with_fields(line, EC=ec_xml({i: "A(左側) ST6 反転2 " + text for i, text in ST6_EC.items()}))
        elif new == "Stm_A_Rev_Axis001_Auto":
            line = with_fields(line, EC=ec_xml({1: "A(左側) ST6 原点位置移動開始"}))
        elif new == "HMI_Stm_A_Rev_Axis001_MovePos_Degree":
            line = with_fields(line, EC=ec_xml({1: "A(左側) ST6 原点位置設定角度", 2: "A(左側) ST6 反転位置設定角度"}))
        table = add_decl(table, line)
    changes[names["globals"]] = table
    added_declarations = {"globals": [n for n, _ in GLOBAL_PAIRS.values()]}
    # 元のST4コメントのST6チャック誤記も承認内容へ合わせる。
    for name, text in texts.items():
        if not text.startswith("[SLWD"):
            continue
        table = changes.get(name, text)
        decls = declarations(table)
        for variable in ("ST4_A_Rev1_M", "Pause", "Error_M"):
            if variable not in decls:
                continue
            line = decls[variable]
            ec = {int(e.get("EK").strip("[]")): e.get("C") for e in ET.fromstring(parse_decl(line).get("EC", "<ECs/>"))}
            if variable == "ST4_A_Rev1_M":
                ec[10], ec[12] = "A(左側) ST4 ワーク不一致エラー", "【Y708】A(左側) ST4 反転1チャック閉"
            else:
                ec[12] = "A(左側) ST6 反転2 ワーク不一致"
            new_line = with_fields(line, EC=ec_xml(ec))
            table = table.replace(line, new_line, 1)
        if table != text:
            changes[name] = table
    # 使用する要求配列の要素コメントをグローバルと参照宣言へ同期。
    ec_add = {
        "Out_CYw_Rev_02_Pick_A_H_Auto": {1: "A(左側) ST6 反転前戻", 2: "A(左側) ST6 設置後戻"},
        "Out_CYw_Rev_02_Pick_A_F_Auto": {1: "A(左側) ST6 反転前行", 2: "A(左側) ST6 設置行"},
        "Out_CYS_Pos_06_Stopper_A_H_Auto": {2: "A(左側) ST6 原点位置移動"},
    }
    for key in ("globals", "movements_vars", "io_vars"):
        name = names[key]
        table = changes.get(name, texts[name])
        for variable, values in ec_add.items():
            if variable not in declarations(table):
                continue
            line = declarations(table)[variable]
            ec = {int(e.get("EK").strip("[]")): e.get("C") for e in ET.fromstring(parse_decl(line).get("EC", "<ECs/>"))}
            ec.update(values)
            table = table.replace(line, with_fields(line, EC=ec_xml(ec)), 1)
        changes[name] = table

    # ローカルの追加。既存の名前・スコープを崩さず、Axis001だけに分離する。
    for key in ("movements_vars", "other_vars"):
        name = names[key]
        table = changes.get(name, texts[name])
        old_decls = declarations(texts[name])
        if key == "movements_vars":
            pairs = [("ST4_A_Rev1_Busy", "ST6_A_Rev2_Busy", "A(左側) ST6 反転2動作中"), ("ST4_A_Rev_End", "ST6_A_Rev2_End", "A(左側) ST6 反転2動作完了")]
        else:
            pairs = [(old, old.replace("Axis000", "Axis001"), "A(左側) ST6 反転2 " + {
                "ZeroSet": "位置ゼロ設定", "HomeWithParameter": "原点復帰FB", "Power": "電源ON状態", "MoveAbsolute": "絶対位置決めFB",
                "MoveVel": "速度", "MoveAcc": "加速度", "MoveDec": "減速度", "MoveBusy": "移動中", "MoveError": "移動エラー", "TON": "完了保持タイマー",
            }[old.split("Axis000_")[1]]) for old in old_decls if old.startswith("Stm_A_Rev_Axis000_") and parse_decl(old_decls[old])["G"] == "VAR"]
            assert len(pairs) == 10
        added_declarations[key] = []
        for old, new, comment in pairs:
            line = with_fields(old_decls[old], N=new, Com=comment)
            table = add_decl(table, line)
            added_declarations[key].append(new)
        changes[name] = table

    # 新規/変更行の使用変数を走査して、足りない外部参照だけ追加する。
    global_table = declarations(changes[names["globals"]])
    scopes = {"st4": "movements_vars", "st6": "movements_vars", "cv": "movements_vars", "motion": "other_vars", "error": "mode_vars", "output": "io_vars"}
    for key, scope in scopes.items():
        name = names[scope]
        table = changes.get(name, texts[name])
        refs = set()
        for row in [json.loads(l) for l in changes[names[key]].splitlines() if l.strip()]:
            for node in walk(row):
                value = node.get("Var", "")
                if value and value not in ("TRUE", "FALSE", "P_On", "P_Off") and re.match(r"^[A-Za-z_]", value) and "#" not in value:
                    refs.add(re.split(r"[.\[]", value, 1)[0])
                if node.get("__type") == "IST" and key == "motion" and node.get("EID") == inline_eid:
                    refs.add("Homing_Para_Stm_Rev2")
        for var in sorted(refs - set(declarations(table))):
            assert var in global_table, (scope, var)
            line = with_fields(global_table[var], G="VAR_EXTERNAL")
            line = re.sub(r"\t(?:AT|RO)=[^\t\r\n]*", "", line)
            table = add_decl(table, line, external=True)
            added_declarations.setdefault(scope, []).append(var)
        changes[name] = table
    # 追加後に要求配列のコメントをグローバルから参照側にも一致させる。
    for key in ("movements_vars", "io_vars"):
        name = names[key]
        table = changes[name]
        for var in ec_add:
            if var in declarations(table):
                line = declarations(table)[var]
                table = table.replace(line, with_fields(line, EC=parse_decl(global_table[var])["EC"]), 1)
        changes[name] = table

    # HMI向けメタ情報を６変数分追加。元のHMI角度表は実体ARRAYなのにメタ側Doubleのため、新規側だけ配列型へ対応。
    metadata = texts[names["metadata"]]
    new_nodes = []
    for old, (new, comment) in GLOBAL_PAIRS.items():
        matches = list(re.finditer(r'<Variable\s[^<>]*\bName="' + re.escape(old) + r'"[^<>]*/>', metadata))
        assert len(matches) == 1, old
        node = ET.fromstring(matches[0][0])
        node.set("Name", new)
        node.set("Address", "new_Controller_0." + new)
        node.set("Comment", comment)
        node.set("Id", str(uuid.uuid4()))
        if new == "HMI_Stm_A_Rev_Axis001_MovePos_Degree":
            node.set("DataTypeName", "Double(99)")
        new_nodes.append(ET.tostring(node, encoding="unicode"))
    marker = "  </VariableGroup>"
    assert marker in metadata
    changes[names["metadata"]] = metadata.replace(marker, "".join("    " + node + "\r\r\n" for node in new_nodes) + marker, 1)

    # 変更・追加した全構成を検証する。
    for key in ("globals", "movements_vars", "other_vars", "mode_vars", "io_vars"):
        before, after = declarations(texts[names[key]]), declarations(changes[names[key]])
        assert len(after) == len([l for l in changes[names[key]].splitlines() if l.startswith("++D=")])
        for var, line in before.items():
            a, b = parse_decl(line), parse_decl(after[var])
            a.pop("EC", None)
            b.pop("EC", None)
            assert a == b, (key, var)
        for var, line in after.items():
            decl = parse_decl(line)
            if decl["G"] == "VAR_EXTERNAL":
                assert decl["D"] == parse_decl(global_table[var])["D"], (key, var)
                if var not in before:
                    assert "AT" not in decl
    oem_root = ET.fromstring(changes[oem_name])
    ids = [e.get("id") for e in oem_root.iter("Entity")]
    assert len(ids) == len(set(ids))
    assert sum(e.get("type") == "Inline" and e.get("name") == inline_eid and e.get("trackingId") == inline_eid for e in oem_root.iter("Entity")) == 1
    ET.fromstring(changes[names["metadata"]])
    for n in original:
        if n.endswith(".dat"):
            assert n not in changes
    assert sum(c.get("__type") == "ST" and c.get("Var") == "ST4_A_Rev1_M[10]" and not c.get("RS") and not c.get("S") for c in st4[7]["CLs"]) == 1
    assert sum(c.get("__type") == "ST" and c.get("Var") == "ST6_A_Rev2_M[10]" and not c.get("RS") and not c.get("S") for c in st6[7]["CLs"]) == 1
    assert all(not any("Rev_02_" in n.get("Var", "") for n in walk(row)) for row in st4)
    for key, indices in (("st4", {7, 9, 10}), ("output", {94, 97, 142}), ("cv", {0})):
        old_lines, new_lines = texts[names[key]].splitlines(), changes[names[key]].splitlines()
        assert len(old_lines) == len(new_lines)
        assert all(a == b for i, (a, b) in enumerate(zip(old_lines, new_lines)) if i not in indices)
    assert changes[names["motion"]].startswith(texts[names["motion"]])
    ladder_counts = {n: len([l for l in changes.get(n, texts[n]).splitlines() if l.strip()]) for n in original_ladders}
    with zipfile.ZipFile(STAGED, "w") as z:
        z.comment = archive_comment
        for info in infos:
            raw = original[info.filename]
            if info.filename in changes:
                raw = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + changes[info.filename].encode("utf-8")
            z.writestr(info, raw)
        for name, raw in additions.items():
            z.writestr(name, raw, compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist() == list(original) + list(additions)
        assert all(z.read(n) == raw for n, raw in original.items() if n not in changes)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == DATA["source_sha256"]
    report = {
        "source": str(SOURCE), "destination": str(DESTINATION), "staged": str(STAGED),
        "source_sha256": DATA["source_sha256"], "output_sha256": hashlib.sha256(STAGED.read_bytes()).hexdigest(),
        "original_entries": len(original), "changed_entries": list(changes), "added_entries": list(additions),
        "edited_rows": edited_rows, "added_declarations": added_declarations,
        "inline_eid": inline_eid, "inline_entity_id": inline_entity_id,
        "ladder_counts": ladder_counts, "native_validation": None, "delta_audit": None,
        "app_build_verified": False, "machine_transfer_performed": False,
        "remaining_source_findings": [
            "ST4/ST6の180度側は角度転送のみで、別の移動開始指令はコピー元にない。今回の３点以外の順序は保持。",
            "ST4/ST6の不一致判定M[7]はPause解除時の立上り復帰を使う既存構成を保持。",
            "出力インターロックのMtr_Flip_01/02_BusyはIOローカルで、MC_MoveAbsoluteのBusyと未接続。今回接続を新設しない。",
            "コンベア完了待ちのST4_End未接続は元のまま。ST6の仮完了接点だけ新ST6_Endへ対応。",
            "新規の反転２設定角度・速度/加減速は初期値未指定。HMI画面・実機設定は未編集。",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("ladder_counts", "added_declarations", "remaining_source_findings")}, ensure_ascii=False, indent=2))


def publish():
    report = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    assert report["native_validation"] and all("PARSE_FAIL=0 MODEL_FAIL=0" in v for v in report["native_validation"].values())
    assert report["delta_audit"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report["source_sha256"]
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest() == report["output_sha256"]
    with STAGED.open("rb") as incoming, DESTINATION.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    note = [
        "ST6_A_Rev2_左反転2への展開（20261026D→E）", "原本Dは保全。PLC接続・転送なし。",
        "ST6：ST6_A_Rev2_M、Busy、End。位置6のワーク/ストッパー、Station_A_Data[6]、反転2のピックアップ/チャック、Axis001へ対応。",
        "承認済み修正：ST4のチャック閉/完了を反転1へ、ST4/6の不一致監視をM[10]へ、M[10]はリセットでなく通常コイルへ。",
        "ST6専用のError_M[12]/Pause[12]と再開時の許可・解除を追加。共通死点停止出力と既存の非常停止/ドア条件は保持。",
        "Output：位置6ストッパー戻、反転2ピックアップ戻/行に自動要求[2]を並列追加。他313行は保持。",
        "CV完了待ち：ST6_Ins_Cv_Rdyの仮接点をST6_A_Rev2_Endへ対応。",
        "CV2A_KED：既存Axis000の４行をもとにAxis001用４行（電源・原点設定ST・原点復帰/ゼロ設定・絶対位置決め）を追加。",
        "反転2のHoming_Para_Stm_Rev2、指令角度/設定角度/Auto/Doneを追加。原点パラメータの数値はコピー元を踏襲。",
        "変数・要素・行コメントを短いST6表記へ対応。EtherCAT/I/O AT・軸設定.datは変更なし。HMIの画面本文は未編集。",
        "", "【未解決：実機運転前に別途確認・修正が必要】",
    ]
    note += report["remaining_source_findings"]
    note += [
        "モータの電源ON条件もコピー元のNOT M9999を踏襲して追加したため、読み込み後のビルド確認だけで実機へ転送しないこと。",
        "原点速度/方向/信号、角度/速度/加減速、可動域、シリンダとモータのインターロックを実機仕様で確認すること。",
        f"全{len(report['ladder_counts'])}セクション/{sum(report['ladder_counts'].values())}行のメーカー同梱読込み/変換と独自差分検査を実施。",
        "Sysmac画面表示・全体ビルド・メーカーシミュレーター・実機動作は未確認。これは動作検証済みプログラムではない。",
    ]
    DESTINATION.with_suffix(".変更内容.txt").write_text("\n".join(note) + "\n", encoding="utf-8-sig")
    assert hashlib.sha256(DESTINATION.read_bytes()).hexdigest() == report["output_sha256"]
    print("保存完了", DESTINATION)


if __name__ == "__main__":
    publish() if "--publish" in sys.argv else build()
