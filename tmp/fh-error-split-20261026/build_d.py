"""現行C版のFHエラー／一時停止を４ステーションへ分離し、D版を生成する。"""
from pathlib import Path
import collections
import copy
import hashlib
import itertools
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
SOURCE = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261026C.smc2"))
DESTINATION = SOURCE.with_name(SOURCE.name.replace("20261026C", "20261026D"))
STAGED = BASE / DESTINATION.name
REPORT = BASE / "verification.json"
EXPECTED_SOURCE = "79d4d646b4dc16af4b42b91dbf5f1068143e13d70547c53a24a4bbb8c0cbca8c"
IDS = {
    "error": "78e4916a-67ab-4f3b-bfbd-e0ecf92fccf4.xml",
    "st5": "9d70f8e1-594f-4023-b6ae-7d63d464a215.xml",
    "fh": "fdce7b3c-0b49-4708-9024-8a98fe6b24b5.xml",
}
STATIONS = [(3, "A(左側) ST1", 0), (9, "A(左側) ST5", 1), (10, "B(右側) ST1", 2), (11, "B(右側) ST5", 3)]


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


def set_field(line, key, value):
    pattern = re.compile(r"(?<=\t)" + re.escape(key) + r"=[^\t\r\n]*")
    return pattern.sub(lambda m: key + "=" + value, line) if pattern.search(line) else line + "\t" + key + "=" + value


def ec_xml(ec):
    return "<ECs>" + "".join('<EC EK="[%s]" C="%s" />' % (i, escape(c, {'"': '&quot;', '\r': '&#xD;', '\n': '&#xA;'})) for i, c in sorted(ec.items())) + "</ECs>"


def normalize(row):
    """新規回路のセル・引数とレール・配線へ一意なIxを振る。"""
    index = 0
    for cell in row["CLs"]:
        for node in walk(cell):
            if node.get("__type") in ("LD", "ST", "F", "FB", "PRM"):
                node["Ix"] = index
                index += 1
            if "Id" in node:
                node["Id"] = str(uuid.uuid4())
    row["LRI"], row["RRI"] = index, index + 1
    ids = {}
    for wire in row.get("VLs", []):
        if wire["Ix"] not in ids:
            ids[wire["Ix"]] = index + 2 + len(ids)
        wire["Ix"] = ids[wire["Ix"]]
    coords = [(c.get("X", 0), c.get("Y", 0)) for c in row["CLs"]]
    assert len(coords) == len(set(coords))
    return row


def new_ld(var, x=0, y=0, neg=False):
    cell = {"__type": "LD", "Var": var, "X": x, "Y": y}
    if neg:
        cell["Not"] = True
    return cell


def new_st(var, x, y=0, reset=False, setting=False):
    cell = {"__type": "ST", "Var": var, "X": x, "Y": y}
    if reset:
        cell["RS"] = True
    if setting:
        cell["S"] = True
    return cell


def station_row(source_row, bit, label, source_branch_rows):
    cells = []
    # 既存の各異常入力とメッセージをステーション単位へ移し、条件を変えない。
    for y, source_y in enumerate(source_branch_rows):
        branch = [copy.deepcopy(c) for c in source_row["CLs"] if c.get("X", 0) < 3 and c.get("Y", 0) == source_y]
        for cell in branch:
            cell["Y"] = y
        assert branch
        cells.extend(branch)
    hold_y = len(source_branch_rows)
    cells += [new_ld(f"Error_M[{bit}]", y=hold_y),
              {"__type": "HL", "X": 1, "Y": hold_y}, {"__type": "HL", "X": 2, "Y": hold_y},
              new_ld("In_Sw_RESET", x=3, neg=True), new_st(f"Error_M[{bit}]", 4),
              new_st(f"Pause[{bit}]", 4, 1, setting=True), new_st("Out_TDC_Stop", 4, 2, setting=True)]
    wires = [{"Ix": 0, "X": 3, "Y": y} for y in range(hold_y)]
    wires += [{"Ix": 1, "X": 4, "Y": y} for y in range(2)]
    return normalize({"CLs": cells, "CMT": f"FH {label} エラー／一時停止", "VLs": wires})


def restart_row(original):
    # 既存の全始動条件（ドア・非常停止等）を同じ順序・属性で保ち、FHの追加３接点を直列追加。
    conditions = sorted([copy.deepcopy(c) for c in original["CLs"] if c.get("X", 0) < 19], key=lambda c: c.get("X", 0))
    assert len(conditions) == 19 and conditions[-1]["Var"] == "M9999"
    before = copy.deepcopy(conditions)
    conditions = conditions[:-1] + [new_ld(f"Error_M[{i}]", neg=True) for i in (9, 10, 11)] + conditions[-1:]
    for x, cell in enumerate(conditions):
        cell["X"], cell["Y"] = x, 0
    contact_x = len(conditions)
    coil_x = contact_x + 1
    cells = conditions
    wires = []
    y = 0
    # 元のPause[1]～[8]の解除に、[9]～[11]を追加。ワーク不一致も当該Pauseでのみ解除。
    for bit in range(1, 12):
        outputs = ["Out_TDC_Stop"]
        if bit == 3:
            outputs.append("ST1_A_Ca1_M[6]")
        elif bit == 9:
            outputs.append("ST5_A_Ca2_M[6]")
        outputs.append(f"Pause[{bit}]")
        cells.append(new_ld(f"Pause[{bit}]", contact_x, y))
        for offset, var in enumerate(outputs):
            cells.append(new_st(var, coil_x, y + offset, reset=True))
        wires += [{"Ix": bit, "X": coil_x, "Y": y + offset} for offset in range(len(outputs) - 1)]
        y += len(outputs)
    wires += [{"Ix": 100, "X": contact_x, "Y": i} for i in range(y - 2)]
    row = normalize({"CLs": cells, "CMT": original.get("CMT", "") + "\r\nFHはST別のError_M／Pauseで判定・解除", "VLs": wires})
    # 追加接点を除いた左側条件の命令・属性は元のまま。
    def no_layout(c):
        return {k: v for k, v in c.items() if k not in ("X", "Y", "Ix")}
    assert [no_layout(c) for c in before] == [no_layout(c) for c in conditions if c.get("X", 0) < contact_x and c["Var"] not in ("Error_M[9]", "Error_M[10]", "Error_M[11]")]
    return row


def energized(row, values):
    """配線の限定ブールモデル。FBの時間挙動・PLCスキャンは検証しない。"""
    graph = collections.defaultdict(list)
    max_y = max([c.get("Y", 0) for c in row["CLs"]] + [w.get("Y", 0) + 1 for w in row.get("VLs", [])])
    for c in row["CLs"]:
        x, y = c.get("X", 0), c.get("Y", 0)
        condition = True
        if c["__type"] in ("LD", "FB"):
            condition = values.get(c.get("Var"), False)
            if c.get("Not"):
                condition = not condition
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


def build():
    assert not DESTINATION.exists(), "既存D版を上書きしません"
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SOURCE, "調査後にC版が更新されました"
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original = {n: z.read(n) for n in z.namelist()}
        infos, archive_comment = z.infolist(), z.comment
    texts = {}
    ladders = {}
    for n, raw in original.items():
        try:
            t = raw.decode("utf-8-sig")
        except UnicodeError:
            continue
        texts[n] = t
        if t.lstrip().startswith("{"):
            try:
                rows = [json.loads(l) for l in t.splitlines() if l.strip()]
            except json.JSONDecodeError:
                continue
            if rows and all("CLs" in r for r in rows):
                ladders[n] = rows
    names = {k: next(n for n in texts if n.endswith(s)) for k, s in IDS.items()}
    # 新番号がプログラム内で実使用されていないことを、配列名全体で確認する。
    for n, rows in ladders.items():
        for row in rows:
            for node in walk(row):
                assert not re.fullmatch(r"(?:Error_M|Pause)\[(?:9|10|11)\]", node.get("Var", "")), (n, node)
    errors = ladders[names["error"]]
    assert len(errors) == 19
    source_error = errors[11]
    assert any(c.get("Var") == "ST5_A_Ca2_M[6]" for c in source_error["CLs"])
    new_rows = [station_row(source_error, bit, label, branches) for (bit, label, line), branches in zip(STATIONS, [(0, 1, 5), (6, 2, 7), (3,), (4,)])]
    new_restart = restart_row(errors[18])
    changes = {}
    # 既存19行中の他17行は原文を保持。FH行を４行へ差し替え、再開行だけ連動変更。
    lines = texts[names["error"]].splitlines(keepends=True)
    ending = "\r\n" if lines[11].endswith("\r\n") else "\n"
    lines[18] = json.dumps(new_restart, ensure_ascii=False, separators=(",", ":")) + ending
    lines[11:12] = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) + ending for r in new_rows]
    changes[names["error"]] = "".join(lines)
    assert len(lines) == 22
    # A左ST5のみPause[9]を参照。A左ST1のPause[3]はそのまま。
    reference_changes = []
    for key, indexes in (("st5", range(len(ladders[names["st5"]]))), ("fh", range(8, 16))):
        name = names[key]
        lines = texts[name].splitlines(keepends=True)
        for i in indexes:
            row = copy.deepcopy(ladders[name][i])
            count = 0
            for node in walk(row):
                if node.get("Var") == "Pause[3]":
                    node["Var"] = "Pause[9]"
                    count += 1
            if count:
                lines[i] = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + ending
                reference_changes.append({"entry": name, "row": i, "count": count})
        changes[name] = "".join(lines)
    assert sum(x["count"] for x in reference_changes) == 13
    # 使用する各スコープで配列要素コメントを一致させる。型・AT・保持設定等は変えない。
    declarations_changed = []
    for name, text in texts.items():
        if not text.startswith("[SLWD"):
            continue
        lines = text.splitlines(keepends=True)
        updated = False
        for i, line in enumerate(lines):
            if not line.startswith("++D="):
                continue
            decl = parse_decl(line.rstrip("\r\n"))
            if decl.get("N") not in ("Error_M", "Pause", "Error_TON", "ST1_A_Ca1_M"):
                continue
            if decl["N"] in ("Error_M", "Pause"):
                assert decl["D"].upper() == "ARRAY[0..99] OF BOOL"
                additions = {bit: "FH " + label for bit, label, _ in STATIONS}
            elif decl["N"] == "Error_TON":
                additions = {2: "A(左側) ST1 測定タイムアウト", 4: "A(左側) ST5 測定タイムアウト"}
            else:
                additions = {6: "A(左側) ST1 検査前ワーク不一致"}
            ec = {int(e.get("EK").strip("[]")): e.get("C") for e in ET.fromstring(decl.get("EC", "<ECs/>"))}
            ec.update(additions)
            old_line = line.rstrip("\r\n")
            lines[i] = set_field(old_line, "EC", ec_xml(ec)) + ("\r\n" if line.endswith("\r\n") else "\n")
            if lines[i] != line:
                declarations_changed.append((name, decl["N"]))
                updated = True
        if updated:
            changes[name] = "".join(lines)

    # 独自の配線モデルでステーション間の分離と再開条件を総当たり検証する。
    cases = 0
    input_specs = [
        ["FH_5552_10_A_Auto", "Error_TON[2]", "FH_Line0_Error_Status_1", "ST1_A_Ca1_M[6]"],
        ["FH_A_ST5_Auto", "Error_TON[4]", "FH_Line1_Error_Status_1", "ST5_A_Ca2_M[6]"],
        ["FH_Line2_Error_Status_1"], ["FH_Line3_Error_Status_1"],
    ]
    # 共通RESETと４組の入力・自己保持の全組合せ。全ステーションが混線しないことを確認。
    keys = [v for group in input_specs for v in group] + [f"Error_M[{bit}]" for bit, _, _ in STATIONS] + ["In_Sw_RESET"]
    for flags in itertools.product((False, True), repeat=len(keys)):
        values = dict(zip(keys, flags))
        for row, (bit, label, line), spec in zip(new_rows, STATIONS, input_specs):
            trigger = values[spec[0]] if len(spec) == 1 else values[spec[0]] and values[spec[1]] or values[spec[2]] or values[spec[3]]
            expected = (trigger or values[f"Error_M[{bit}]"]) and not values["In_Sw_RESET"]
            result = energized(row, values)
            assert result[f"Error_M[{bit}]"] == expected
            assert result[f"Pause[{bit}]"] == expected
            assert result["Out_TDC_Stop"] == expected
        cases += 1
    restart_cases = 0
    for allowed in (False, True):
        for pause in range(12):
            for blocking in range(12):
                values = {"In_Sw_START": allowed, "AutoMode": True,
                          **{f"Pause[{i}]": i == pause for i in range(1, 12)},
                          **{f"Error_M[{i}]": i == blocking for i in range(1, 12)}}
                result = energized(new_restart, values)
                permission = allowed and blocking == 0
                assert result["ST1_A_Ca1_M[6]"] == (permission and pause == 3)
                assert result["ST5_A_Ca2_M[6]"] == (permission and pause == 9)
                for i in range(1, 12):
                    assert result[f"Pause[{i}]"] == (permission and pause == i)
                restart_cases += 1

    # ZIP、原文保持、既存宣言（EC以外）と物理ATを照合。
    new_ladders = {}
    for name, old_rows in ladders.items():
        rows = [json.loads(l) for l in changes.get(name, texts[name]).splitlines() if l.strip()]
        new_ladders[name] = rows
    changed_error_lines = changes[names["error"]].splitlines()
    source_error_lines = texts[names["error"]].splitlines()
    assert changed_error_lines[:11] == source_error_lines[:11]
    assert changed_error_lines[15:21] == source_error_lines[12:18]
    assert all(a == b for a, b in zip(texts[names["fh"]].splitlines()[:8], changes[names["fh"]].splitlines()[:8]))
    for name in changes:
        if texts[name].startswith("[SLWD"):
            before = {parse_decl(l)["N"]: parse_decl(l) for l in texts[name].splitlines() if l.startswith("++D=")}
            after = {parse_decl(l)["N"]: parse_decl(l) for l in changes[name].splitlines() if l.startswith("++D=")}
            assert set(before) == set(after)
            for var in before:
                a, c = before[var], after[var]
                a.pop("EC", None)
                c.pop("EC", None)
                assert a == c, (name, var)
    for bit, _, _ in STATIONS:
        coils = [(name, i) for name, rows in new_ladders.items() for i, row in enumerate(rows)
                 for c in row["CLs"] if c.get("__type") == "ST" and c.get("Var") == f"Error_M[{bit}]"]
        assert len(coils) == 1, (bit, coils)
    assert not any(name.endswith((".dat", ".oem")) for name in changes)
    assert not any(name.endswith("09c1f70b-b9ac-4e5d-884f-9779e69a597a.xml") for name in changes)
    with zipfile.ZipFile(STAGED, "w") as z:
        z.comment = archive_comment
        for info in infos:
            raw = original[info.filename]
            if info.filename in changes:
                raw = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + changes[info.filename].encode("utf-8")
            z.writestr(info, raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.namelist() == list(original) and z.testzip() is None
        assert all(z.read(n) == raw for n, raw in original.items() if n not in changes)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SOURCE
    report = {
        "source": str(SOURCE), "destination": str(DESTINATION), "staged": str(STAGED),
        "source_sha256": EXPECTED_SOURCE, "output_sha256": hashlib.sha256(STAGED.read_bytes()).hexdigest(),
        "entries": len(original), "changed_entries": list(changes), "stations": STATIONS,
        "declaration_comments_updated": declarations_changed, "pause_reference_changes": reference_changes,
        "boolean_station_input_cases": cases, "boolean_restart_cases": restart_cases,
        "ladder_counts": {n: len(rows) for n, rows in new_ladders.items()}, "native_validation": None,
        "output_section_unchanged": True, "physical_io_and_settings_unchanged": True,
        "app_build_verified": False, "machine_transfer_performed": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("ladder_counts", "declaration_comments_updated", "pause_reference_changes")}, ensure_ascii=False, indent=2))


def publish():
    report = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    assert report["native_validation"] and all("PARSE_FAIL=0 MODEL_FAIL=0" in v for v in report["native_validation"].values())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report["source_sha256"]
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest() == report["output_sha256"]
    with STAGED.open("rb") as incoming, DESTINATION.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    note = ["FHエラー・一時停止を４ステーションへ分離（20261026C→D）", "原本C版を保持。B側の表記はプロジェクトのB(右側)に統一。", ""]
    note += [f"{label}：FH Line{line}、Error_M[{bit}]、Pause[{bit}]" for bit, label, line in STATIONS]
    note += [
        "", "A左ST1：Line0異常・10秒タイムアウトError_TON[2]・ST1_A_Ca1_M[6]。",
        "A左ST5：Line1異常・10秒タイムアウトError_TON[4]・ST5_A_Ca2_M[6]。",
        "B右ST1/ST5：現行Cに検査シーケンスがないため、既存のLine2/Line3異常のみ。未実装の測定要求・タイムアウト・ワーク不一致を勝手に新設しない。",
        "A左ST5本体とFHのST5画像処理はPause[3]→Pause[9]。A左ST1はPause[3]を維持。",
        "再開条件にError_M[9]/[10]/[11]のb接点を追加。既存の非常停止・ドア等の条件は保持。",
        "Pause[3]再開時はST1のM[6]のみ、Pause[9]再開時はST5のM[6]のみリセット。Pause[10]/[11]の解除も追加。",
        "エラーと一時停止の保持はST別だが、Out_TDC_Stopは設備共通のため、いずれのFH異常でも従来同様に死点停止要求を出す。設備を独立運転化したものではない。",
        "共通RESETスイッチと各Lineのエラークリア処理（100ms）は従来通り。HMIメッセージ番号・送信先は変更なし。",
        "複数異常の同時発生時は共用HMI_MessageNo[0]に後段の代入が優先。ST別に行を分けたため、４行間ではA-ST1→A-ST5→B-ST1→B-ST5の後段優先となる。各Error_Mは別々に保持される。",
        "行コメント・配列要素コメントを対応。コピー元ST1 M[6]のST2表記誤りをST1へ修正。",
        "出力セクション316行・EtherCAT/I/O AT・その他機器設定を保持。",
        f"検証：ZIP CRCと元データ保持。同梱読込み変換で全{len(report['ladder_counts'])}セクション／{sum(report['ladder_counts'].values())}行。",
        f"独自配線ブール検査：４ステーションの入力・保持・RESET {report['boolean_station_input_cases']}組、再開条件{report['boolean_restart_cases']}組。タイマーやPLCスキャンの実行試験ではない。",
        "Sysmacでの全体ビルド・画面表示・実機動作は未確認。PLC接続・転送なし。使用前に全体ビルドと停止／リセット／再開をオフライン確認してください。",
    ]
    DESTINATION.with_suffix(".変更内容.txt").write_text("\n".join(note) + "\n", encoding="utf-8-sig")
    assert hashlib.sha256(DESTINATION.read_bytes()).hexdigest() == report["output_sha256"]
    print("保存完了", DESTINATION)


if __name__ == "__main__":
    publish() if "--publish" in sys.argv else build()
