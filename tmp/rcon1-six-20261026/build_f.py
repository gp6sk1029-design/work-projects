"""承認された条件でRCON1を６軸へ展開し、コメントを軸用途で統一する。"""
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
DESTINATION = SOURCE.with_name(SOURCE.name.replace("20261026E", "20261026F"))
STAGED = BASE / DESTINATION.name
REPORT = BASE / "verification.json"
AXES = {
    1: ("A(左側)", "NG1排出(上下降)", "NG1上下降"),
    2: ("B(右側)", "NG1排出(上下降)", "NG1上下降"),
    3: ("A(左側)", "ストックフォルダ(SF)／NG2排出(送り)", "SF/NG2送り"),
    4: ("B(右側)", "ストックフォルダ(SF)／NG2排出(送り)", "SF/NG2送り"),
    5: ("A(左側)", "ストックフォルダ(SF)／NG2排出(上下降)", "SF/NG2上下降"),
    6: ("B(右側)", "ストックフォルダ(SF)／NG2排出(上下降)", "SF/NG2上下降"),
}
IDS = {
    "rcon": "7b1666c7-ee97-4210-81b2-fed5a6172074.xml",
    "globals": "f07dd06c-505c-431b-b9fc-098949805b4e.xml",
    "other_vars": "a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml",
    "metadata": "20a6b651-4c34-401a-965e-db3e18414d5c.xml",
}
ALIASES = {
    "RCON1_OUT_TargetPos_mm": "目標位置 [mm]",
    "RCON1_OUT_PositionBand_mm": "位置決め幅 [mm]",
    "RCON1_OUT_Speed_mm_s": "指令速度 [mm/s]",
    "RCON1_OUT_AccDec_G": "共通加減速度 [G]",
    "RCON1_OUT_PushLimit_pct": "押付け制限 [%]（未使用）",
    "RCON1_ActualPos_mm": "現在位置 [mm]",
    "RCON1_Current_mA": "指令電流 [mA]（監視値）",
    "RCON1_ActualSpeed_mm_s": "現在速度 [mm/s・符号付き]",
    "RCON1_AlarmCode": "軸異常コード",
    "RCON1_DataValid": "入力有効（安全許可ではない）",
}
STATUS = {
    "PositionDone": "位置決め完了", "HomeDone": "原点復帰完了", "Moving": "移動中",
    "Alarm": "軸異常", "ServoReady": "サーボON状態", "PushMiss": "押付け空振り（未使用）",
    "OverloadWarning": "過負荷警告", "CommandDone": "指令完了", "Zone1": "ゾーン1内",
    "Zone2": "ゾーン2内", "ControllerReady": "コントローラ準備完了", "EmergencyStop": "非常停止状態（入力）",
}
CONTROL = {
    "Start": "移動開始要求（100ms保持）", "Home": "原点復帰要求（未接続）", "Pause": "一時停止要求（未接続）",
    "Reset": "異常リセット要求", "ServoOn": "サーボON要求（非常停止時OFF）",
    "InchingSelect": "インチング選択（OFF=ジョグ）", "JogSpeedSelect": "ジョグ速度切替（未接続）",
    "JogMinus": "原点方向ジョグ（未接続）", "JogPlus": "反原点方向ジョグ（未接続）",
    "GainSelect0": "ゲイン選択下位（未使用）", "GainSelect1": "ゲイン選択上位（未使用）",
    "PushEnable": "押付け選択（未使用・OFF=位置決め）", "PushDirection": "押付け方向（未使用）",
    "RelativeMove": "相対移動選択（未使用・OFF=絶対）",
    "BrakeRelease": "ブレーキ強制解除要求（非常停止でない間ON）",
}
ROW_TITLES = [
    "目標位置 [mm]（転送未接続：P_Off）", "位置決め幅 [mm]（転送未接続：P_Off）",
    "指令速度 [mm/s]（転送未接続：P_Off）", "共通加減速度 [G]（転送未接続：P_Off）",
    "押付け制限 [%]（未使用：P_Off）", "移動開始要求（立上り・100ms保持）", "原点復帰要求（未接続：P_Off）",
    "一時停止要求（未接続：P_Off）", "異常リセット（RESET・共通Pause[5]）",
    "サーボON要求（非常停止時OFF）", "インチング選択（OFF=ジョグ）", "ジョグ速度切替（未接続：P_Off）",
    "原点方向ジョグ（未接続：P_Off）", "反原点方向ジョグ（未接続：P_Off）",
    "ゲイン選択下位（未使用）", "ゲイン選択上位（未使用）", "押付け選択（未使用・OFF=位置決め）",
    "押付け方向（未使用）", "相対移動選択（未使用・OFF=絶対）",
    "ブレーキ強制解除（非常停止でない間ON：要確認）",
    "現在位置 [mm]（監視転送未接続：P_Off）", "指令電流 [mA]（監視転送未接続：P_Off）",
    "現在速度 [mm/s・符号付き]（監視転送未接続：P_Off）", "軸異常コード（監視転送未接続：P_Off）",
    "入力有効（監視転送未接続：P_Off）", "位置決め完了", "原点復帰完了", "移動中", "軸異常",
    "サーボON状態", "押付け空振り（未使用・読取無効）", "過負荷警告", "指令完了", "ゾーン1内", "ゾーン2内",
    "コントローラ準備完了", "非常停止状態（入力）", "動作準備（準備完了・サーボON・異常なし）",
    "開始保持（要求1～3・準備100ms）", "動作完了（位置決め完了立上り・100ms保持）",
]


def prefix(axis):
    side, _, short = AXES[axis]
    return f"{side} RCON1_{axis} {short}"


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def parse_decl(line):
    return dict(p.split("=", 1) for p in line[2:].split("\t") if "=" in p)


def declarations(text):
    return {parse_decl(line)["N"]: line for line in text.splitlines() if line.startswith("++D=")}


def with_fields(line, **fields):
    parts = line[2:].split("\t")
    for key, value in fields.items():
        index = next((i for i, p in enumerate(parts) if p.startswith(key + "=")), None)
        if index is None:
            parts.append(key + "=" + value)
        else:
            parts[index] = key + "=" + value
    return "++" + "\t".join(parts)


def ec_dict(line):
    return {e.get("EK"): e.get("C") for e in ET.fromstring(parse_decl(line).get("EC", "<ECs/>"))}


def ec_xml(ec):
    return "<ECs>" + "".join('<EC EK="%s" C="%s" />' % (escape(k, {'"': '&quot;'}), escape(v, {'"': '&quot;', '\r': '&#xD;', '\n': '&#xA;'})) for k, v in ec.items()) + "</ECs>"


def add_decl(text, line, external=False):
    assert parse_decl(line)["N"].lower() not in {n.lower() for n in declarations(text)}, parse_decl(line)["N"]
    if external or "+GN=VAR_GLOBAL" in text:
        return text + line + "\r\n"
    marker = "+GN=VAR_EXTERNAL"
    assert text.count(marker) == 1
    return text.replace(marker, line + "\r\n" + marker, 1)


def source_map(axis, globals_old):
    result = {n: n.replace("RCON1_1_", f"RCON1_{axis}_", 1) for n in globals_old if n.startswith("RCON1_1_")}
    result.update({n: n.replace("RCON1_", f"RCON1_{axis}_", 1) for n in ALIASES})
    result["RCON1_IAI_Auto"] = f"RCON1_{axis}_Auto"
    return result


def transform_var(value, axis, mapping):
    for old in sorted(mapping, key=len, reverse=True):
        if value == old or value.startswith(old + "[") or value.startswith(old + "."):
            return mapping[old] + value[len(old):]
    value = value.replace("RCON1_OUT[1]", f"RCON1_OUT[{axis}]").replace("RCON1_IN[1]", f"RCON1_IN[{axis}]")
    if value == "TimerQ_In_SenCY_NG1_Pick_A_H":
        return "TimerQ_In_SenCY_NG1_Pick_B_H" if axis == 2 else "P_Off"
    return value


def var_description(old):
    if old in ALIASES:
        return ALIASES[old]
    if old.startswith("RCON1_1_IN_"):
        return STATUS[old[len("RCON1_1_IN_"):]]
    return {
        "RCON1_1_Ready": "動作準備（安全許可とは別）", "RCON1_1_Error": "異常管理用予備（未接続）",
        "RCON1_1_Error_Clear": "異常解除用予備（未接続）", "RCON1_1_M": "開始・完了保持",
        "RCON1_IAI_Auto": "自動移動要求",
    }[old]


def apply_axis_comment(line, old, axis):
    line = with_fields(line, Com=prefix(axis) + " " + var_description(old))
    if old == "RCON1_1_M":
        line = with_fields(line, EC=ec_xml({"[1]": prefix(axis) + " 開始指令保持", "[2]": prefix(axis) + " 動作完了100ms"}))
    elif old == "RCON1_IAI_Auto":
        if axis == 1:
            ec = ec_dict(line)
            ec = {k: prefix(axis) + " " + v for k, v in ec.items()}
        else:
            ec = {f"[{i}]": prefix(axis) + f" 自動要求{i}（外部接続用）" for i in range(1, 4)}
        line = with_fields(line, EC=ec_xml(ec))
    return line


def axis_rows(template, axis, mapping):
    rows = copy.deepcopy(template)
    mapping = {**mapping, "RCON1_1_TON": f"RCON1_{axis}_TON", "RCON1_1_TOF": f"RCON1_{axis}_TOF"}
    for i, row in enumerate(rows):
        if axis != 1:
            for node in walk(row):
                if isinstance(node.get("Var"), str):
                    node["Var"] = transform_var(node["Var"], axis, mapping)
                if "Id" in node:
                    node["Id"] = str(uuid.uuid4())
        title = ROW_TITLES[i]
        if i == 5:
            title += "／NG1戻センサ条件" if axis <= 2 else "／条件未確定：P_Offで禁止"
        if i == 6 and axis >= 3:
            title += "／インターロック未確定"
        group = {0: "【出力値】 /////////////////////////////////////", 5: "【出力信号】 /////////////////////////////////////",
                 20: "【入力値】 /////////////////////////////////////", 25: "【入力信号】 /////////////////////////////////////",
                 37: "【動作管理】 /////////////////////////////////////"}.get(i)
        row["CMT"] = (group + "\r\n" if group else "") + title
        if i == 0:
            side, role, _ = AXES[axis]
            row["CMT"] = f"#{side} RCON1_{axis}/Node1/ {role}\r\n" + row["CMT"]
    return rows


def build():
    assert not DESTINATION.exists(), "既存F版を上書きしません"
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == DATA["source_sha256"], "調査後にE版が更新されました"
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original = {n: z.read(n) for n in z.namelist()}
        infos, archive_comment = z.infolist(), z.comment
    texts = DATA["texts"]
    names = {k: next(n for n in texts if n.endswith(v)) for k, v in IDS.items()}
    global_text = texts[names["globals"]]
    globals_old = declarations(global_text)
    family = [n for n in globals_old if n.startswith("RCON1_1_")] + list(ALIASES) + ["RCON1_IAI_Auto"]
    assert len(family) == 27, family
    assert "TimerQ_In_SenCY_NG1_Pick_B_H" in globals_old
    for axis in range(2, 7):
        assert not any(n.startswith(f"RCON1_{axis}_") for n in globals_old)
    changes, new_globals = {}, {}
    old_to_new = {}
    new_names_by_axis = {}
    for axis in range(2, 7):
        mapping = source_map(axis, globals_old)
        new_names_by_axis[axis] = mapping
        for old in family:
            new = mapping[old]
            line = with_fields(globals_old[old], N=new, Const="0", RO="0")
            line = apply_axis_comment(line, old, axis)
            global_text = add_decl(global_text, line)
            new_globals[new] = line
            old_to_new[new] = old
    assert len(new_globals) == 135
    # 既存軸１の名前は動作プログラムが使用中なので変更せず、用途・説明だけ統一する。
    for old in family:
        line = declarations(global_text)[old]
        global_text = global_text.replace(line, apply_axis_comment(line, old, 1), 1)
    hmi_old = declarations(global_text)["HMI_RCON1_OUT_TargetPos"]
    global_text = global_text.replace(hmi_old, with_fields(hmi_old, Com=prefix(1) + " HMI設定位置 [mm]"), 1)

    # 構造体と軸別フラグの要素にも、同じ軸用途を表示する。型定義自体は共有のため変更しない。
    for var in ("RCON1_OUT", "RCON1_IN"):
        line = declarations(global_text)[var]
        ec = ec_dict(line)
        for axis in range(1, 7):
            side, role, _ = AXES[axis]
            ec[f"[{axis}]"] = f"{side} RCON1_{axis} {role}"
            if var == "RCON1_OUT":
                for member, text in [("TargetPos_mm", ALIASES["RCON1_OUT_TargetPos_mm"]), ("PositionBand_mm", ALIASES["RCON1_OUT_PositionBand_mm"]),
                                     ("Speed_mm_s", ALIASES["RCON1_OUT_Speed_mm_s"]), ("AccDec_G", ALIASES["RCON1_OUT_AccDec_G"]), ("PushLimit_pct", ALIASES["RCON1_OUT_PushLimit_pct"])]:
                    ec[f"[{axis}].{member}"] = prefix(axis) + " " + text
                for member, text in CONTROL.items():
                    ec[f"[{axis}].Control.{member}"] = prefix(axis) + " " + text
            else:
                for member, text in [("ActualPos_mm", ALIASES["RCON1_ActualPos_mm"]), ("Current_mA", ALIASES["RCON1_Current_mA"]),
                                     ("ActualSpeed_mm_s", ALIASES["RCON1_ActualSpeed_mm_s"]), ("AlarmCode", ALIASES["RCON1_AlarmCode"]), ("DataValid", ALIASES["RCON1_DataValid"])]:
                    ec[f"[{axis}].{member}"] = prefix(axis) + " " + text
                for member, text in STATUS.items():
                    ec[f"[{axis}].Status.{member}"] = prefix(axis) + " " + text
        global_text = global_text.replace(line, with_fields(line, Com="RCON1/Node1 6軸 " + ("出力（PLC→RCON）" if var.endswith("OUT") else "入力（RCON→PLC）"), EC=ec_xml(ec)), 1)
    for var, line in list(declarations(global_text).items()):
        decl = parse_decl(line)
        if not var.startswith("RCON1_") or var in ("RCON1_OUT", "RCON1_IN"):
            continue
        ec = ec_dict(line)
        if decl["D"].upper().startswith("ARRAY[1..6]"):
            for axis in range(1, 7):
                key = f"[{axis}]"
                if key in ec:
                    desc = re.sub(r"^\d軸目（No\.\d）", "", ec[key]).strip()
                    ec[key] = prefix(axis) + " " + desc
            global_text = global_text.replace(line, with_fields(line, EC=ec_xml(ec)), 1)
        elif var in ("RCON1_RxRaw", "RCON1_RxWord", "RCON1_TxWord", "RCON1_TxUInt"):
            for key, comment in list(ec.items()):
                word = int(key.strip("[]"))
                if 8 <= word <= 55:
                    axis = (word - 8) // 8 + 1
                    ec[key] = re.sub(str(axis) + r"軸目", prefix(axis), comment, count=1)
            global_text = global_text.replace(line, with_fields(line, EC=ec_xml(ec)), 1)
    # 既存のNode1軸別物理ワードは割付を保持してコメントに用途を追加する。
    for var, line in list(declarations(global_text).items()):
        decl = parse_decl(line)
        match = re.fullmatch(r"E001_(?:Out_OUT|In_IN)(\d\d)_.*", var)
        if not match or not decl.get("AT", "").startswith("ECAT://node#1/"):
            continue
        word = int(match[1])
        if not 8 <= word <= 55:
            continue
        axis = (word - 8) // 8 + 1
        comment = decl.get("Com", "")
        # 紙面/ネットワークのワード番号は残し、先頭の一般的な軸表記だけ用途へ置換。
        comment = re.sub(r"RCON1\s*", "", comment, count=1)
        comment = re.sub(str(axis) + r"軸目\s*", "", comment, count=1)
        global_text = global_text.replace(line, with_fields(line, Com=prefix(axis) + " " + comment.strip()), 1)
    changes[names["globals"]] = global_text
    all_globals = declarations(global_text)

    # 各軸のラダー40行×6＋既存共通通信６行。通信STは複製せず本文を完全保持する。
    old_rows = [json.loads(l) for l in texts[names["rcon"]].splitlines() if l.strip()]
    assert len(old_rows) == 46 and all(not any(c.get("__type") == "IST" for c in r["CLs"]) for r in old_rows[:40])
    template = old_rows[:40]
    axis_blocks = {1: axis_rows(template, 1, {})}
    for axis in range(2, 7):
        axis_blocks[axis] = axis_rows(template, axis, new_names_by_axis[axis])
    core = copy.deepcopy(old_rows[40:])
    core_titles = ["入力読込み・現在値復元", "OUT数値変換・制御bit組立", "許可条件付き実I/O書込み"]
    for index, row in enumerate(core):
        controller = 1 if index < 3 else 2
        if index % 3 == 0:
            row["CMT"] = f"#RCON{controller}/Node{1 if controller == 1 else 5}/ {6 if controller == 1 else 5}軸共通通信\r\n"
        else:
            row["CMT"] = ""
        row["CMT"] += "【" + core_titles[index % 3] + "】\r\n" + ["読取り専用。DataValidは安全許可ではない。", "内部計算のみ。実出力代入は次のST。", "書込み許可OFFは更新保留。停止指令ではない。"][index % 3]
    new_rows = [r for axis in range(1, 7) for r in axis_blocks[axis]] + core
    assert len(new_rows) == 246
    for before, after in zip(old_rows[40:], core):
        assert before["CLs"] == after["CLs"] and before.get("VLs") == after.get("VLs")
    changes[names["rcon"]] = "\r\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in new_rows) + "\r\n"

    # 全既存外部参照へコメントだけ同期し、追加５軸のTON/TOFをローカル実体として登録する。
    timer_names = ["RCON1_1_TOF", "RCON1_1_TON"]
    for name, text in texts.items():
        if not text.startswith("[SLWD") or name == names["globals"]:
            continue
        table = text
        for var, line in list(declarations(table).items()):
            if var in all_globals:
                new_decl = parse_decl(all_globals[var])
                old_decl = parse_decl(line)
                changed = line
                if var.startswith("RCON1") or var.startswith("HMI_RCON1") or var.startswith("E001_") and new_decl.get("Com") != old_decl.get("Com"):
                    if "Com" in new_decl:
                        changed = with_fields(changed, Com=new_decl["Com"])
                    if "EC" in new_decl:
                        changed = with_fields(changed, EC=new_decl["EC"])
                if changed != line:
                    table = table.replace(line, changed, 1)
        if name == names["other_vars"]:
            local_old = declarations(text)
            for axis in range(1, 7):
                for old in timer_names:
                    new = old.replace("RCON1_1_", f"RCON1_{axis}_")
                    desc = "開始要求100ms保持" if old.endswith("TOF") else "準備・完了タイマー"
                    ec = {"[1]": prefix(axis) + (" 開始要求100ms保持" if old.endswith("TOF") else "準備100ms確認")}
                    if old.endswith("TON"):
                        ec["[2]"] = prefix(axis) + " 動作完了100ms保持"
                    line = with_fields(local_old[old], N=new, Com=prefix(axis) + " " + desc, EC=ec_xml(ec))
                    if axis == 1:
                        table = table.replace(declarations(table)[new], line, 1)
                    else:
                        line = with_fields(line, Const="0", RO="0")
                        table = add_decl(table, line)
            for var, line in new_globals.items():
                external = with_fields(line, G="VAR_EXTERNAL")
                assert "AT" not in parse_decl(external)
                table = add_decl(table, external, external=True)
            # 軸２のB側センサは、既存グローバルへの参照のみ追加する。
            sensor = "TimerQ_In_SenCY_NG1_Pick_B_H"
            if sensor not in declarations(table):
                table = add_decl(table, with_fields(all_globals[sensor], G="VAR_EXTERNAL"), external=True)
        if table != text:
            changes[name] = table

    # メタ情報：既存コメントを同期し、新規グローバル135個を同じ名前/型/可変属性で追加する。
    meta_name = names["metadata"]
    metadata = texts[meta_name]
    root = ET.fromstring(metadata)
    old_meta = {e.get("Name"): e for e in root.iter("Variable")}
    for var, element in old_meta.items():
        if var not in all_globals:
            continue
        comment = parse_decl(all_globals[var]).get("Com", "")
        if element.get("Comment", "") == comment:
            continue
        pattern = re.compile(r'<Variable\s[^<>]*\bName="' + re.escape(var) + r'"[^<>]*/>')
        matches = list(pattern.finditer(metadata))
        assert len(matches) == 1, var
        old_xml = matches[0][0]
        new_element = copy.deepcopy(element)
        new_element.set("Comment", comment)
        metadata = metadata[:matches[0].start()] + ET.tostring(new_element, encoding="unicode").strip() + metadata[matches[0].end():]
    new_elements = []
    for var, line in new_globals.items():
        old = old_to_new[var]
        if old not in old_meta:
            # コントローラで自動生成された変数を元に、実体型に対応する既知のメタ形を選ぶ。
            data_type = parse_decl(line)["D"].upper()
            expected = {"BOOL": "Boolean", "LREAL": "Double", "DINT": "Integer", "UINT": "UShort", "ARRAY[0..99] OF BOOL": "Boolean(99)"}[data_type]
            source_meta = next(e for e in old_meta.values() if e.get("DataTypeName") == expected and e.get("Group") == "VAR_GLOBAL")
        else:
            source_meta = old_meta[old]
        e = copy.deepcopy(source_meta)
        e.set("Name", var)
        e.set("Address", "new_Controller_0." + var)
        e.set("Comment", parse_decl(line)["Com"])
        e.set("Id", str(uuid.uuid4()))
        e.set("IsConstant", "false")
        e.set("IsReadOnly", "false")
        e.set("IsControllerVariable", "false")
        e.set("IsReadOnlyNetwork", "false")
        e.set("Retained", "false")
        e.set("InitialValue", "")
        e.tail = None
        new_elements.append(ET.tostring(e, encoding="unicode"))
    marker = "  </VariableGroup>"
    assert marker in metadata
    changes[meta_name] = metadata.replace(marker, "".join("    " + e + "\r\r\n" for e in new_elements) + marker, 1)

    # 型・属性・宣言・重複書込み・軸の混線・原本保全を検査する。
    for n, old_text in texts.items():
        if n not in changes or not old_text.startswith("[SLWD"):
            continue
        before, after = declarations(old_text), declarations(changes[n])
        assert len(after) == len([l for l in changes[n].splitlines() if l.startswith("++D=")])
        assert len(after) == len({x.lower() for x in after})
        for var, line in before.items():
            a, c = parse_decl(line), parse_decl(after[var])
            for key in ("Com", "EC"):
                a.pop(key, None)
                c.pop(key, None)
            assert a == c, (n, var)
        for var, line in after.items():
            decl = parse_decl(line)
            if var in new_globals or re.fullmatch(r"RCON1_[2-6]_TO[NF]", var):
                assert decl.get("Const") == "0" and decl.get("RO") == "0"
            if decl["G"] == "VAR_EXTERNAL":
                assert decl["D"].upper() == parse_decl(all_globals[var])["D"].upper(), (n, var)
                if var not in before:
                    assert "AT" not in decl
    other_decls = declarations(changes[names["other_vars"]])
    for row in new_rows[:240]:
        for node in walk(row):
            val = node.get("Var", "")
            if not val or val in ("P_On", "P_Off", "TRUE", "FALSE") or "#" in val:
                continue
            base = re.split(r"[.\[]", val, 1)[0]
            assert base in other_decls, val
    for axis in range(2, 7):
        block = axis_blocks[axis]
        joined = json.dumps(block)
        assert "RCON1_OUT[1]" not in joined and "RCON1_IN[1]" not in joined
        assert not re.search(r'RCON1_1_(?:M|TON|TOF|IN_|Ready)', joined)
        assert "RCON1_IAI_Auto" not in joined
        expected_sensor = "TimerQ_In_SenCY_NG1_Pick_B_H" if axis == 2 else "P_Off"
        assert block[5]["CLs"][1]["Var"] == expected_sensor
        assert block[6]["CLs"][1]["Var"] == expected_sensor
        assert block[19]["CLs"][0] == template[19]["CLs"][0]
        assert block[19]["CLs"][1]["Var"] == f"RCON1_OUT[{axis}].Control.BrakeRelease"
    assert all(axis_blocks[axis][0]["CMT"].startswith("#" + AXES[axis][0]) for axis in AXES)
    old_no_comment = copy.deepcopy(template)
    new_no_comment = copy.deepcopy(axis_blocks[1])
    for row in old_no_comment + new_no_comment:
        row.pop("CMT", None)
    assert old_no_comment == new_no_comment, "既存軸１の動作は変更しません"
    guids = [n["Id"] for block in axis_blocks.values() for row in block for n in walk(row) if "Id" in n]
    assert len(guids) == len(set(guids))
    ET.fromstring(changes[meta_name])
    assert len(list(ET.fromstring(changes[meta_name]).iter("Variable"))) == len(old_meta) + 135
    ladder_counts = {}
    for n, t in texts.items():
        if not t.lstrip().startswith("{"):
            continue
        try:
            rows = [json.loads(l) for l in changes.get(n, t).splitlines() if l.strip()]
        except json.JSONDecodeError:
            continue
        if rows and all(isinstance(r, dict) and "CLs" in r for r in rows):
            ladder_counts[n] = len(rows)
    assert not any(n.endswith((".dat", ".oem")) for n in changes)
    assert sum(n in changes for n in ladder_counts) == 1
    with zipfile.ZipFile(STAGED, "w") as z:
        z.comment = archive_comment
        for info in infos:
            raw = original[info.filename]
            if info.filename in changes:
                raw = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + changes[info.filename].encode("utf-8")
            z.writestr(info, raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist() == list(original)
        assert all(z.read(n) == raw for n, raw in original.items() if n not in changes)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == DATA["source_sha256"]
    changed_comments = [var for var, line in all_globals.items() if var in globals_old and parse_decl(line).get("Com") != parse_decl(globals_old[var]).get("Com")]
    report = {
        "source": str(SOURCE), "destination": str(DESTINATION), "staged": str(STAGED),
        "source_sha256": DATA["source_sha256"], "output_sha256": hashlib.sha256(STAGED.read_bytes()).hexdigest(),
        "entries": len(original), "changed_entries": list(changes), "axes": AXES,
        "global_added": list(new_globals), "local_timers_added": 10, "external_added": 136,
        "existing_global_comments_changed": changed_comments, "metadata_variables_added": 135,
        "rcon_row_count_before": 46, "rcon_row_count_after": 246, "common_st_texts_unchanged": True,
        "existing_axis1_logic_unchanged": True, "error_and_emergency_stop_logic_unchanged": True,
        "brake_release_same_as_axis1": True, "start_condition_axis2": "TimerQ_In_SenCY_NG1_Pick_B_H",
        "start_condition_axes3_to_6": "P_Off", "ladder_counts": ladder_counts,
        "native_validation": None, "native_variable_attributes": None, "delta_audit": None,
        "app_build_verified": False, "machine_transfer_performed": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("global_added", "existing_global_comments_changed", "ladder_counts")}, ensure_ascii=False, indent=2))


def publish():
    report = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    assert report["native_validation"] and all("PARSE_FAIL=0 MODEL_FAIL=0" in x for x in report["native_validation"].values())
    assert report["native_variable_attributes"] and report["delta_audit"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report["source_sha256"]
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest() == report["output_sha256"]
    with STAGED.open("rb") as incoming, DESTINATION.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    notes = ["RCON1 ６軸展開（20261026E→F）", "原本Eを保持。PLC接続・転送なし。", "", "【軸の用途】"]
    notes += [f"RCON1_{axis} = {side} {role}" for axis, (side, role, _) in AXES.items()]
    notes += [
        "", "【今回の変更】", "軸別ラダー40行を５軸分（200行）追加。RCON_IAIは46→246行。末尾の共通通信ST６本の本文は完全保持。",
        "グローバル135個、OtherDeviceのTON/TOF計10個、外部参照136個（新規135＋既存B側センサ）を追加。新規の可変変数はConst=0/RO=0を明示。",
        "軸1の既存変数名・動作は保持。RCON1_OUT_TargetPos_mm等の軸番号なし旧名は軸1専用としてコメント明記。",
        "新規軸はRCON1_n_OUT_TargetPos_mm等の設定値、RCON1_n_ActualPos_mm等の監視値、RCON1_n_IN_*、Ready、M、Autoを各軸へ分離。",
        "RCON1_n_Error／Error_Clearはコピー元と同じ予備変数（未接続）。実際のReset要求はRESETと共通Pause[5]の条件。",
        "ユニット先頭の行コメントは#。行コメント／グローバル／外部参照／構造体要素／軸別共通配列／Node1実割付ワードへ用途を統一。",
        "", "【ユーザー回答に従った条件】",
        "軸2の開始インターロックはB側NG1ピックアップ戻。軸3～6の開始/原点インターロックはP_Off（未確定）。原点要求接点自体は元からP_Offのまま。",
        "全６軸のブレーキ強制解除は軸1と同じNOT M9999。非常停止でない間ONとなる。上下降軸の落下/保持対策を確認するまで実機へ転送しない。",
        "既存のError_M[5]／Pause[5]／M9999等の停止判定は変更しない。追加軸2～6のAlarm/非常停止状態を、この共通判定へ自動追加していない。別途停止連動の設計が必要。",
        "", "【テンプレートの未接続部分・検証限界】",
        "目標位置/幅/速度/加減速/押付け設定の転送、現在位置/電流/速度/異常コード/DataValidの監視転送は、軸1の元ラダーと同じP_Offで未接続。これらを有効化した完成シーケンスではない。",
        "構造体RCON1_IN[n]自体は既存共通STが復元する。RCON1_n_ActualPos_mm等の別名監視値は上記転送未接続なので更新されない。",
        "ReadyはControllerReady・ServoReady・異常無の論理値であり、安全許可ではない。開始受付PEND OFF確認や開始/完了の異常監視は元のまま（新設なし）。",
        "WriteEnable／AxisApply／MotionPermit／LayoutConfirmed／ByteOrderConfirmed／CommOKの設定・判定は変更していない。OFF時の更新保留を停止とみなさない。",
        "位置/速度/ストローク/押付け等の実機値は新しく決めていない。軸3～6の機械条件も未確定。",
        f"全{len(report['ladder_counts'])}セクション/{sum(report['ladder_counts'].values())}行の同梱ラダー読込み/変換、同梱SLWD読込みによる新規変数Const/RO検査、独自差分検査を実施。",
        "Sysmac画面での全体ビルド・シミュレーター・実機動作は未確認。前回のST6定数扱い等、画面状態まで検証済みとは報告しない。",
        "EtherCATのAT・全.dat・全他ラダー・非常停止/異常停止/出力セクションを保持。今回の用途表と実機の軸No.0～5の対応は使用前に照合すること。",
    ]
    DESTINATION.with_suffix(".変更内容.txt").write_text("\n".join(notes) + "\n", encoding="utf-8-sig")
    assert hashlib.sha256(DESTINATION.read_bytes()).hexdigest() == report["output_sha256"]
    print("保存完了", DESTINATION)


if __name__ == "__main__":
    publish() if "--publish" in sys.argv else build()
