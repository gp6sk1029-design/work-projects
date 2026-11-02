"""利用者更新後のG版を保全し、Node9の既存20変数だけを再割付する。"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base.parent))
from read_nrbf_data import Reader

source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261023G.smc2"))
prior = source.with_name(source.name.replace("20261023G", "20261023E"))
destination = source.with_name(source.name.replace("20261023G", "20261023H"))
staged = base / destination.name
report_path = base / "verification.json"
global_id = "f07dd06c-505c-431b-b9fc-098949805b4e.xml"

def get_globals(archive):
    entry = next(n for n in archive.namelist() if n.endswith(global_id))
    text = archive.read(entry).decode("utf-8-sig")
    rows = {}
    for line in text.splitlines():
        if line.startswith("++"):
            row = dict(x.split("=", 1) for x in line[2:].split("\t") if "=" in x)
            assert row["N"] not in rows
            rows[row["N"]] = row
    return entry, text, rows

def build():
    assert not destination.exists(), "既存H版は上書きしません"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    with zipfile.ZipFile(source) as archive:
        original = {n: archive.read(n) for n in archive.namelist()}
        infos, comment = archive.infolist(), archive.comment
        global_name, global_text, original_globals = get_globals(archive)
    with zipfile.ZipFile(prior) as archive:
        _, _, previous_globals = get_globals(archive)
    targets = {n: row for n, row in previous_globals.items() if row.get("AT", "").startswith("ECAT://node#9/")}
    assert len(targets) == 20
    # 配線順の根拠は以前の実割付と現在のNode9のPDO。名称からは推測しない。
    physical = {n: row for n, row in targets.items() if "/In Bit" in row["AT"]}
    assert len(physical) == 16
    used = sorted((int(re.search(r"In Bit(\d+)$", row["AT"])[1]), n) for n,row in physical.items())
    assert [bit for bit, name in used] == list(range(16))
    assert [n for bit, n in used[:8]] == [
        "In_Sen_Unl_Conv_A_Pass", "In_Sen_Unl_Conv_B_Pass",
        "In_Sen_Trs_Conv_A_Arrival", "In_Sen_Trs_Conv_B_Arrival",
        "In_SenCY_Hnd_Feed_A_H", "In_SenCY_Hnd_Feed_A_F",
        "In_SenCY_Hnd_Feed_B_H", "In_SenCY_Hnd_Feed_B_F",
    ]
    network_entry = next(n for n in original if n.endswith("22aaf14a-1b6b-4d6b-8ef3-92d6b44c6fa5.dat"))
    network = Reader(original[network_entry]).parse()
    node = next(v for v in network.objects.values() if isinstance(v, dict) and v.get("StationAddress") == 9)
    assert network.deref(node["Profile"]) == "00000083:00000034:00010002:GX-ID1612"
    assert network.deref(node["PdoMapping1b00/Pdo0"]).startswith("6100:01:")
    assert node["PdoMapping1b00/BitLength"] == 16
    assert {int(re.search(r"Division(\d+)/ID$", k)[1]) for k in node if re.search(r"PdoMapping1B00/Pdo6100:01/Division\d+/ID$", k)} == set(range(16))
    assert network.deref(node["PdoMapping1bff/Pdo0"]).startswith("2002:01:")
    for name, row in targets.items():
        assert name in original_globals and not original_globals[name].get("AT"), name
        assert row["D"] == original_globals[name]["D"], name
    count = 0
    def assign(match):
        nonlocal count
        name = match[1]
        if name not in targets:
            return match[0]
        count += 1
        return match[0] + "AT=" + targets[name]["AT"] + "\t"
    updated = re.sub(r"\bN=([^\t\r\n]+)\t", assign, global_text)
    assert count == 20
    raw = original[global_name]
    replacement = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + updated.encode("utf-8")
    with zipfile.ZipFile(staged,"w") as archive:
        archive.comment = comment
        for info in infos:
            archive.writestr(info, replacement if info.filename == global_name else original[info.filename])
    with zipfile.ZipFile(staged) as archive:
        assert archive.namelist() == list(original) and archive.testzip() is None
        _, _, after = get_globals(archive)
        assert after.keys() == original_globals.keys()
        for name, old in original_globals.items():
            if name in targets:
                assert after[name] == {**old, "AT": targets[name]["AT"]}
            else:
                assert after[name] == old
        all_addresses = [r["AT"] for r in after.values() if r.get("AT")]
        assert len(all_addresses) == len(set(all_addresses)), "同一ポートへの二重割付"
        assert sum(r.get("AT", "").startswith("ECAT://node#9/") for r in after.values()) == 20
        for name in original:
            if name != global_name:
                assert archive.read(name) == original[name], name
        ladder_counts = {}
        references = set()
        for name in archive.namelist():
            try: text = archive.read(name).decode("utf-8-sig")
            except UnicodeError: continue
            if text.lstrip().startswith("{"):
                try: rows = [json.loads(line) for line in text.splitlines() if line.strip()]
                except json.JSONDecodeError: continue
                if rows and all(isinstance(r,dict) and "CLs" in r for r in rows):
                    ladder_counts[name] = len(rows)
                    references.update(n for n in targets if re.search(r"\b" + re.escape(n) + r"\b", text))
        # 使用中の8変数は既存プログラムから引き続き参照され、名前を変更していない。
        assert {name for bit,name in used[:8]} <= references
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    report = {"source":str(source), "destination":str(destination), "staged":str(staged),
              "source_sha256":source_hash, "output_sha256":hashlib.sha256(staged.read_bytes()).hexdigest(),
              "entries":len(original), "changed_entries":[global_name], "node":9,
              "node_profile":"GX-ID1612", "input_bits":16,"used_bits":8,"spare_bits":8,
              "restored_variables":{n:r["AT"] for n,r in targets.items()},
              "program_and_other_entries_byte_identical":True,"ladder_counts":ladder_counts,
              "native_validation":None,"app_build_verified":False,"machine_transfer_performed":False}
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("restored_variables","ladder_counts")},ensure_ascii=False))

def publish():
    report=json.loads(report_path.read_text(encoding="utf-8"))
    assert report["native_validation"] and all("PARSE_FAIL=0 MODEL_FAIL=0" in v for v in report["native_validation"].values())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==report["source_sha256"]
    assert hashlib.sha256(staged.read_bytes()).hexdigest()==report["output_sha256"]
    with staged.open("rb") as incoming,destination.open("xb") as outgoing:shutil.copyfileobj(incoming,outgoing)
    assert hashlib.sha256(destination.read_bytes()).hexdigest()==report["output_sha256"]
    print("保存完了",destination)

if __name__=="__main__":
    publish() if "--publish" in sys.argv else build()
