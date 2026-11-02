"""F版の112Byte Node1へ既存変数を再割付し、必要な受信範囲だけを補正する。"""
from pathlib import Path
import collections
import copy
import hashlib
import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
base = Path(__file__).resolve().parent
sys.path.insert(0, str(base.parent))
from read_nrbf_data import Reader

source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261023F.smc2"))
prior = source.with_name(source.name.replace("20261023F", "20261023E"))
destination = source.with_name(source.name.replace("20261023F", "20261023G"))
staged = base / destination.name
report_path = base / "verification.json"
global_id = "f07dd06c-505c-431b-b9fc-098949805b4e.xml"
local_id = "a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml"
metadata_id = "20a6b651-4c34-401a-965e-db3e18414d5c.xml"
ladder_id = "7b1666c7-ee97-4210-81b2-fed5a6172074.xml"
esi_path = Path(r"C:\Program Files (x86)\OMRON\Sysmac Studio\IODeviceProfiles\EsiFiles\UserEsiFiles\ESI_IAI_Gateway_ECT_V_1_08_Rev_0.xml")
physical = re.compile(r"E001_(Out_OUT|In_IN)(\d{2})_(200[34])_([0-9A-F]{2})$")

def fields(text):
    return [dict(x.split("=", 1) for x in line[2:].split("\t") if "=" in x)
            for line in text.splitlines() if line.startswith("++")]

def read_global(archive):
    name = next(n for n in archive.namelist() if n.endswith(global_id))
    return name, {r["N"]: r for r in fields(archive.read(name).decode("utf-8-sig"))}

def xml_escape(text):
    return escape(text, {'"': '&quot;', '\r': '&#xD;', '\n': '&#xA;', '\t': '&#x9;'})

def strip_st_comments(text):
    text = re.sub(r"\(\*.*?\*\)", "", text, flags=re.S)
    return re.sub(r"//[^\r\n]*", "", text)

def main():
    assert not destination.exists(), f"既存のG版を上書きしません：{destination}"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    with zipfile.ZipFile(source) as z:
        original = {n: z.read(n) for n in z.namelist()}
        infos, zip_comment = z.infolist(), z.comment
        globals_name, old_globals = read_global(z)
        config_name = next(n for n in original if n.endswith("22aaf14a-1b6b-4d6b-8ef3-92d6b44c6fa5.dat"))
        # NRBFを安全な値として解析し、オブジェクトの実行はしない。
        network = Reader(original[config_name]).parse()
    with zipfile.ZipFile(prior) as z:
        _, old_assignments = read_global(z)
    slave = next(v for v in network.objects.values() if isinstance(v, dict) and v.get("StationAddress") == 1)
    assert network.deref(slave["Profile"]) == "00000588:00A47070:00010008:RCGW-ECT(112Byte/112Byte)"
    esi = ET.parse(esi_path).getroot()
    device = next(v for v in esi.findall(".//Device") if v.findtext("Name") == "RCGW-ECT(112Byte/112Byte)")
    assert device.find("Type").get("ProductCode") == "#x00A47070"
    assert device.find("Type").get("RevisionNo") == "#x00010008"
    bindings = {}
    for direction, pdo_type, mapping, index, prefix in [
        ("OUT", "RxPdo", "1600", "2003", "Out_OUT"),
        ("IN", "TxPdo", "1a00", "2004", "In_IN"),
    ]:
        entries = [e for pdo in device.findall(pdo_type) for e in pdo.findall("Entry")]
        assert len(entries) == 56
        active = {k:v for k,v in slave.items() if re.fullmatch(f"PdoMapping{mapping}/Pdo[0-9]+", k)}
        assert len(active) == 56
        for word, entry in enumerate(entries):
            assert entry.findtext("Index").lower() == f"#x{index}"
            assert int(entry.findtext("SubIndex")) == word + 1
            assert entry.findtext("DataType") == "UINT" and entry.findtext("BitLen") == "16"
            assert entry.findtext("Name") == f"{direction}{word:02d}"
            object_key = network.deref(active[f"PdoMapping{mapping}/Pdo{word}"])
            obj_index, sub, guid = object_key.split(":")
            assert obj_index == index and int(sub, 16) == word + 1
            assert slave[f"{guid}/BitOffset"] == 16 * word and slave[f"{guid}/BitLength"] == 16
            name = f"E001_{prefix}{word:02d}_{index}_{word+1:02X}"
            port = f"{prefix}{word:02d}_{index}_{word+1:02X}"
            expected = f"ECAT://node#1/{port}"
            assert old_assignments[name]["AT"] == expected
            assert old_globals[name]["D"] == "UINT" and not old_globals[name].get("AT")
            bindings[name] = expected

    old_buffer_types = {"RCON1_RxRaw": "ARRAY[0..71] OF UINT", "RCON1_RxWord": "ARRAY[0..71] OF WORD"}
    new_buffer_types = {k:v.replace("0..71", "0..55") for k,v in old_buffer_types.items()}
    outside_comments = {name: f"RCON1 {('OUT' if match[1]=='Out_OUT' else 'IN')}{int(match[2]):02d} 112Byte範囲外（未割付・不使用）"
                        for name in old_globals if (match := physical.fullmatch(name)) and int(match[2]) >= 56}
    assert len(outside_comments) == 32
    changes = {}
    declaration_changes = []
    for name, raw in original.items():
        if not name.endswith((global_id, local_id)):
            continue
        text = raw.decode("utf-8-sig")
        output = []
        for line in text.splitlines(keepends=True):
            if not line.startswith("++"):
                output.append(line)
                continue
            values = dict(x.split("=",1) for x in line[2:].rstrip("\r\n").split("\t") if "=" in x)
            variable = values["N"]
            updated = line
            if name.endswith(global_id) and variable in bindings:
                assert "AT" not in values
                updated = updated.replace(f"\tN={variable}\t", f"\tN={variable}\tAT={bindings[variable]}\t", 1)
            if variable in old_buffer_types:
                assert values["D"] == old_buffer_types[variable]
                updated = updated.replace("++D=" + old_buffer_types[variable], "++D=" + new_buffer_types[variable], 1)
                # 受信配列から消える添字のコメントも同時に外す。
                updated, removed = re.subn(r'<EC EK="\[(?:5[6-9]|6[0-9]|7[01])\]" C="[^"]*"\s*/>', "", updated)
                assert removed == 16, (name, variable, removed)
            if variable in outside_comments:
                updated, count = re.subn(r"(?<=\tCom=)[^\t\r\n]*", outside_comments[variable], updated)
                assert count == 1
            if updated != line:
                declaration_changes.append({"entry":name,"variable":variable,"before":values,
                                            "after":dict(x.split("=",1) for x in updated[2:].rstrip("\r\n").split("\t") if "=" in x)})
            output.append(updated)
        updated = "".join(output)
        if updated != text:
            bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
            changes[name] = bom + updated.encode("utf-8")

    # HMI用の変数情報に存在する物理変数コメントだけを同期する。
    metadata_name = next(n for n in original if n.endswith(metadata_id))
    text = original[metadata_name].decode("utf-8-sig")
    def change_metadata(match):
        tag = match[0]
        node = ET.fromstring(tag)
        name = node.get("Name")
        if name in outside_comments:
            tag = re.sub(r'(\bComment=")[^"]*(")', lambda m: m[1]+xml_escape(outside_comments[name])+m[2], tag)
        if name in new_buffer_types:
            raise AssertionError("受信配列の別型メタデータを追加確認する必要があります")
        return tag
    updated = re.sub(r"<Variable\b[^>]*?\/>", change_metadata, text)
    if updated != text:
        changes[metadata_name] = (b"\xef\xbb\xbf" if original[metadata_name].startswith(b"\xef\xbb\xbf") else b"") + updated.encode("utf-8")

    ladder_name = next(n for n in original if n.endswith(ladder_id))
    ladder_text = original[ladder_name].decode("utf-8-sig")
    old_rows = [json.loads(line) for line in ladder_text.splitlines() if line.strip()]
    assert len(old_rows) == 46
    input_updates = []
    def replace_st(match):
        text = json.loads(match[2])
        new = text
        if "RCON1_RxRaw[71] := E001_In_IN71_2004_48;" in text:
            new, removed = re.subn(r"RCON1_RxRaw\[(5[6-9]|6[0-9]|7[01])\] := E001_In_IN\1_2004_[0-9A-F]{2};[\r\n]*", "", new)
            assert removed == 16
            assert new.count("FOR ConvWordIndex := INT#0 TO INT#71 DO") == 1
            new = new.replace("FOR ConvWordIndex := INT#0 TO INT#71 DO", "FOR ConvWordIndex := INT#0 TO INT#55 DO")
            new = new.replace("まず72個のUINTをRxRawへコピーします。", "112Byte分の56個のUINTをRxRawへコピーします。")
            new = new.replace("軸データはIN08～55。IN56～71は読みますが、用途を勝手に決めません。", "共通領域はIN00～07、6軸分はIN08～55。IN56以降は存在しないため読みません。")
            input_updates.append("RCON1入力：72ワードから56ワードへ変更、IN56～71の読取り16行を削除")
        if "// OUT01～07、OUT56～71は、このSTからは一切書き換えません。" in text:
            new = new.replace("// OUT01～07、OUT56～71は、このSTからは一切書き換えません。",
                              "// OUT01～07は予約領域のため書き換えません。OUT56以降は112Byte設定に存在しません。")
            input_updates.append("RCON1出力：処理は維持し、112Byteに合わせて範囲の注記だけ修正")
        return match[0] if new == text else match[1] + json.dumps(new, ensure_ascii=False)
    new_ladder = re.sub(r'("TXT"\s*:\s*)("(?:\\.|[^"\\])*")', replace_st, ladder_text)
    assert len(input_updates) == 2, input_updates
    changes[ladder_name] = (b"\xef\xbb\xbf" if original[ladder_name].startswith(b"\xef\xbb\xbf") else b"") + new_ladder.encode("utf-8")

    with zipfile.ZipFile(staged,"w") as result:
        result.comment = zip_comment
        for info in infos:
            result.writestr(info,changes.get(info.filename,original[info.filename]))

    # 保存後の独立検証：割付の一意性、外部宣言、実コードの通信範囲、元データ保持。
    with zipfile.ZipFile(staged) as z:
        assert z.namelist() == list(original) and z.testzip() is None
        _, new_globals = read_global(z)
        for name, expected in bindings.items(): assert new_globals[name]["AT"] == expected
        assigned = [r["AT"] for r in new_globals.values() if r.get("AT")]
        assert len(assigned) == len(set(assigned)), "I/O割付の二重登録"
        node1 = [r for r in new_globals.values() if r.get("AT", "").startswith("ECAT://node#1/")]
        assert len(node1) == 112
        for variable, old in old_globals.items():
            new = new_globals[variable]
            allowed = {"AT"} if variable in bindings else set()
            if variable in old_buffer_types: allowed |= {"D", "EC"}
            if variable in outside_comments: allowed |= {"Com"}
            assert {k:v for k,v in old.items() if k not in allowed} == {k:v for k,v in new.items() if k not in allowed}, variable
        assert old_globals.keys() == new_globals.keys()
        for name in original:
            if name not in changes: assert z.read(name) == original[name]
        local_name = next(n for n in z.namelist() if n.endswith(local_id))
        local_rows = fields(z.read(local_name).decode("utf-8-sig"))
        for declaration in local_rows:
            if declaration.get("G") == "VAR_EXTERNAL" and declaration["N"] in new_globals:
                assert declaration["D"].upper() == new_globals[declaration["N"]]["D"].upper(), declaration["N"]
            if declaration["N"] in new_buffer_types:
                assert declaration["D"] == new_buffer_types[declaration["N"]]
                ecs = ET.fromstring(declaration["EC"])
                assert [int(e.get("EK").strip("[]")) for e in ecs] == list(range(56))
        rows = [json.loads(line) for line in z.read(ladder_name).decode("utf-8-sig").splitlines() if line.strip()]
        assert len(rows) == 46
        changed_rows = []
        code_texts=[]
        for ix,(old,new) in enumerate(zip(old_rows,rows)):
            if old != new:
                changed_rows.append(ix)
                a,b=copy.deepcopy(old),copy.deepcopy(new)
                for cell in a["CLs"]: cell.pop("TXT",None)
                for cell in b["CLs"]: cell.pop("TXT",None)
                assert a == b, "ST本文以外のラダーを変更してはならない"
            for cell in new["CLs"]:
                if "TXT" in cell:code_texts.append(strip_st_comments(cell["TXT"]))
        assert changed_rows == [40,42], changed_rows
        code="\n".join(code_texts)
        refs=set(re.findall(r"\bE001_(?:Out_OUT|In_IN)\d{2}_200[34]_[0-9A-F]{2}\b",code))
        assert refs <= bindings.keys()
        assert "E001_Out_OUT00_2003_01_1" not in code
        rx=next(strip_st_comments(c["TXT"]) for c in rows[40]["CLs"] if "TXT" in c)
        rx_pairs=re.findall(r"RCON1_RxRaw\[(\d+)\] := (E001_\w+);",rx)
        assert rx_pairs == [(str(i),f"E001_In_IN{i:02d}_2004_{i+1:02X}") for i in range(56)]
        assert "INT#71" not in rx and "FOR ConvWordIndex := INT#0 TO INT#55 DO" in rx
        writes = re.findall(r"\b(E001_Out_OUT\d{2}_2003_[0-9A-F]{2})\s*:=",code)
        expected_writes = {f"E001_Out_OUT{i:02d}_2003_{i+1:02X}" for i in [0,*range(8,56)]}
        assert len(writes)==49 and set(writes)==expected_writes
        assert all(8+(axis-1)*8+7 <= 55 for axis in range(1,7))
        # RCON2のST3本と、他の全ラダー/STの通信記述は元のまま。
        assert rows[43:] == old_rows[43:]
        ladder_counts={}
        for name in z.namelist():
            try: text=z.read(name).decode("utf-8-sig")
            except UnicodeError:continue
            if text.lstrip().startswith("{"):
                try: units=[json.loads(line) for line in text.splitlines() if line.strip()]
                except json.JSONDecodeError:continue
                if units and all(isinstance(v,dict) and "CLs" in v for v in units):ladder_counts[name]=len(units)
        report={"source":str(source),"destination":str(destination),"staged":str(staged),
                "source_sha256":source_hash,"output_sha256":hashlib.sha256(staged.read_bytes()).hexdigest(),
                "entries":len(original),"changed_entries":list(changes),"ladder_counts":ladder_counts,
                "node1_profile":"RCGW-ECT(112Byte/112Byte)","bindings":bindings,
                "node1_rebound_inputs":56,"node1_rebound_outputs":56,"removed_input_reads":16,
                "buffer_range":"0..55","changed_rcon_rows":changed_rows,
                "unrelated_entries_byte_identical":True,"node5_logic_and_binding_unchanged":True,
                "native_validation":None,"app_build_verified":False,"machine_transfer_performed":False}
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    lines=["方向\tワード番号\t変数名\t型\t割付先\tコメント"]
    for name,address in bindings.items():
        match=physical.fullmatch(name)
        lines.append("\t".join(["出力" if match[1]=="Out_OUT" else "入力",str(int(match[2])),name,"UINT",address,new_globals[name].get("Com","")]))
    (base/"112Byte割付照合.tsv").write_text("\n".join(lines)+"\n",encoding="utf-8-sig")
    print(json.dumps({k:v for k,v in report.items() if k not in ("bindings","ladder_counts")},ensure_ascii=False))

def publish():
    report=json.loads(report_path.read_text(encoding="utf-8"))
    assert report["native_validation"] and all("PARSE_FAIL=0 MODEL_FAIL=0" in v for v in report["native_validation"].values())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==report["source_sha256"]
    assert hashlib.sha256(staged.read_bytes()).hexdigest()==report["output_sha256"]
    with staged.open("rb") as incoming,destination.open("xb") as outgoing:shutil.copyfileobj(incoming,outgoing)
    assert hashlib.sha256(destination.read_bytes()).hexdigest()==report["output_sha256"]
    note="""F版からの変更内容（Node1／RCON1 112Byte対応）

・F版原本を保持し、G版として新規保存。
・Node1のIN00～55とOUT00～55へ、以前のE001変数を同じポート名で再割付（各56個、計112個）。
・RCON1入力STのIN56～71読取り16行を削除。受信配列と正規化ループを0～55へ統一。
・6軸分の位置・速度・状態・制御ビットの変換処理、既存の書込み許可条件は維持。
・OUT01～07の予約領域には書き込まない。範囲外の旧変数32個は未割付のまま残して注記。
・Node5／RCON2、他のラダー、HMI、機器・軸・EtherCAT構成データは変更なし。
・同梱の読込み処理で全ラダーを検査。実アプリでの全体ビルド・実機通信・転送は未実施。

注意：実機側も6軸直接数値指定、112Byte、同じ軸順であることを照合してください。
今回の割付修正で、未確認の通信正常判定・運転許可・安全停止を完成させたわけではありません。
LayoutConfirmed等を確認せずTRUEに変更しないでください。
SysmacでG版を再インポートし、I/Oマップ確認と全体ビルド後に実機確認してください。
"""
    destination.with_suffix(".変更内容.txt").write_text(note,encoding="utf-8-sig")
    print("保存完了",destination)

if __name__=="__main__":
    publish() if "--publish" in sys.argv else main()
