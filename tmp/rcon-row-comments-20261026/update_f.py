"""F版のRCON_IAIの行コメントだけを更新し、バックアップ後に同名保存する。"""
from pathlib import Path
import copy
import hashlib
import json
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent
SOURCE = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261026F.smc2"))
STAGED = BASE / SOURCE.name
REPORT = BASE / "verification.json"
EXPECTED = "d28564e74037f23d8b224db9a2944192be1ed2c6bb56a9abf245164b33710162"
ROLES = {
    1: ("A(左側)", "NG1排出(上下降)", "NG1上下降"),
    2: ("B(右側)", "NG1排出(上下降)", "NG1上下降"),
    3: ("A(左側)", "ストックフォルダ(SF)／NG2排出(送り)", "SF/NG2送り"),
    4: ("B(右側)", "ストックフォルダ(SF)／NG2排出(送り)", "SF/NG2送り"),
    5: ("A(左側)", "ストックフォルダ(SF)／NG2排出(上下降)", "SF/NG2上下降"),
    6: ("B(右側)", "ストックフォルダ(SF)／NG2排出(上下降)", "SF/NG2上下降"),
}


def build():
    before_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert before_hash == EXPECTED, "確認後にF版が更新されました"
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original = {n: z.read(n) for n in z.namelist()}
        infos, archive_comment = z.infolist(), z.comment
    target = next(n for n in original if n.endswith("7b1666c7-ee97-4210-81b2-fed5a6172074.xml"))
    text = original[target].decode("utf-8-sig")
    old_rows = [json.loads(l) for l in text.splitlines() if l.strip()]
    assert len(old_rows) == 246
    new_rows = copy.deepcopy(old_rows)
    changes = []
    for index, row in enumerate(new_rows):
        old_comment = row.get("CMT", "")
        if index < 240:
            axis, local_row = index // 40 + 1, index % 40
            side, full_role, short_role = ROLES[axis]
            if local_row == 0:
                rest = old_comment.split("\r\n", 1)[1]
                row["CMT"] = f"#{side} RCON1_{axis}/Node1/ {full_role}\r\n" + rest
            else:
                prefix = f"{side} RCON1_{axis} {short_role}"
                if old_comment.startswith("【"):
                    row["CMT"] = prefix + "\r\n" + old_comment
                else:
                    row["CMT"] = prefix + "／" + old_comment
        else:
            controller = 1 if index < 243 else 2
            node = 1 if controller == 1 else 5
            if not old_comment.startswith("#"):
                row["CMT"] = f"RCON{controller}/Node{node} 共通通信\r\n" + old_comment
        if row.get("CMT") != old_comment:
            changes.append({"row": index, "before": old_comment, "after": row["CMT"]})
        a, b = dict(old_rows[index]), dict(row)
        a.pop("CMT", None)
        b.pop("CMT", None)
        assert a == b, index
    for axis, (side, role, short_role) in ROLES.items():
        block = new_rows[(axis - 1) * 40:axis * 40]
        assert block[0]["CMT"].startswith("#" + side + f" RCON1_{axis}/Node1/")
        assert all(side in r["CMT"].splitlines()[0] and f"RCON1_{axis}" in r["CMT"].splitlines()[0] for r in block)
    assert len(changes) == 238
    ending = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    for change in changes:
        i = change["row"]
        lines[i] = json.dumps(new_rows[i], ensure_ascii=False, separators=(",", ":")) + ending
    replacement = "".join(lines)
    with zipfile.ZipFile(STAGED, "w") as z:
        z.comment = archive_comment
        for info in infos:
            raw = original[info.filename]
            if info.filename == target:
                raw = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + replacement.encode("utf-8")
            z.writestr(info, raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist() == list(original)
        assert all(z.read(n) == raw for n, raw in original.items() if n != target)
    counts = {}
    for n, raw in original.items():
        try:
            t = raw.decode("utf-8-sig")
        except UnicodeError:
            continue
        if not t.lstrip().startswith("{"):
            continue
        try:
            rows = [json.loads(l) for l in t.splitlines() if l.strip()]
        except json.JSONDecodeError:
            continue
        if rows and all(isinstance(r, dict) and "CLs" in r for r in rows):
            counts[n] = len(rows)
    report = {"source": str(SOURCE), "destination": str(SOURCE), "staged": str(STAGED),
              "source_sha256": before_hash, "output_sha256": hashlib.sha256(STAGED.read_bytes()).hexdigest(),
              "entries": len(original), "changed_entries": [target], "comment_changes": changes,
              "ladder_counts": counts, "native_validation": None, "program_logic_unchanged": True,
              "all_variable_declarations_unchanged": True, "all_network_configuration_unchanged": True,
              "app_build_verified": False, "machine_transfer_performed": False}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("comment_changes", "ladder_counts")}, ensure_ascii=False, indent=2))
    print("変更コメント数", len(changes))


def publish():
    report = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    assert report["native_validation"] and all("PARSE_FAIL=0 MODEL_FAIL=0" in x for x in report["native_validation"].values())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report["source_sha256"]
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest() == report["output_sha256"]
    backup_dir = SOURCE.parent / "PLC_更新前バックアップ"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / (SOURCE.stem + "_行コメント更新前_" + report["source_sha256"][:8] + SOURCE.suffix)
    assert backup.resolve().parent == backup_dir.resolve()
    if backup.exists():
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == report["source_sha256"]
    else:
        with SOURCE.open("rb") as incoming, backup.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == report["source_sha256"]
    # 上書き直前にも確認し、他のアプリによる保存と競合しないようにする。
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report["source_sha256"]
    os.replace(STAGED, SOURCE)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report["output_sha256"]
    report["backup"] = str(backup)
    report["published"] = True
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("更新完了", SOURCE)
    print("更新前バックアップ", backup)


if __name__ == "__main__":
    publish() if "--publish" in sys.argv else build()
