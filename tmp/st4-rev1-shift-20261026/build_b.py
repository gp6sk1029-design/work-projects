"""確認済みの下側[3]以降だけを繰り下げ、A原本を残してB版を作る。"""
from pathlib import Path
import collections
import copy
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
base = Path(__file__).resolve().parent
source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261026A.smc2"))
destination = source.with_name(source.name.replace("20261026A", "20261026B"))
staged = base / destination.name
report_path = base / "verification.json"
target = "ST4_A_Rev1_M"
pattern = re.compile(re.escape(target) + r"\[(\d+)\]")
main_id = "4a05531b-6bae-4cd7-9d4d-e3d6f875d1dc.xml"

def transform(value, move):
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            match = pattern.fullmatch(child) if key == "Var" and isinstance(child, str) else None
            result[key] = target + f"[{int(match[1])+1}]" if match and move and int(match[1]) >= 3 else transform(child, move)
        return result
    if isinstance(value, list):
        return [transform(v, move) for v in value]
    return value

def comment_map(text):
    match = re.search(r"\tEC=([^\t\r\n]*)", text)
    if not match:
        return {}
    root = ET.fromstring(match[1])
    values = {int(e.get("EK").strip("[]")): e.get("C") for e in root}
    assert len(root) == len(values)
    return values

def build():
    assert not destination.exists(), "既存B版は上書きしません"
    before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert before_hash == "ea5d41e9682099c64512ecdf325893b2a24e41c8f789884fa3cc1d9a61204696", "確認後に原本が更新されました"
    with zipfile.ZipFile(source) as archive:
        original = {n: archive.read(n) for n in archive.namelist()}
        infos, comment = archive.infolist(), archive.comment
        assert archive.testzip() is None
    texts = {}
    ladder_counts = {}
    for name, raw in original.items():
        try: text = raw.decode("utf-8-sig")
        except UnicodeError: continue
        texts[name] = text
        if text.lstrip().startswith("{"):
            try: rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            except json.JSONDecodeError: continue
            if rows and all(isinstance(row,dict) and "CLs" in row for row in rows):ladder_counts[name] = len(rows)
    main_name = next(n for n in ladder_counts if n.endswith(main_id))
    main_rows = [json.loads(line) for line in texts[main_name].splitlines() if line.strip()]
    assert len(main_rows) == 9
    assert main_rows[3]["CLs"][5]["Var"] == target + "[3]"
    assert main_rows[4]["CLs"][6]["Var"] == target + "[3]"
    added_comment = main_rows[3]["CMT"]
    replacements = {}
    reference_changes = []
    new_comments = {}
    moved_comments = {}
    # JSONのVarフィールドだけを変更し、その他の命令・レイアウト情報をそのまま残す。
    pair = re.compile(r'("Var"\s*:\s*")(' + re.escape(target) + r'\[(\d+)\])(")')
    for name in ladder_counts:
        text = texts[name]
        if target not in text:
            continue
        lines = text.splitlines(keepends=True)
        number = -1
        before_rows, expected_rows = [], []
        for index,line in enumerate(lines):
            if not line.strip():continue
            number += 1
            row = json.loads(line)
            before_rows.append(row)
            move = not (name == main_name and number <= 3)
            if name != main_name:
                assert not any(pattern.fullmatch(m) and int(pattern.fullmatch(m)[1]) == 3 for m in re.findall(r'"Var":"([^"]+)"',line)), "別セクションの[3]参照は上側/下側の確認が必要"
            expected_rows.append(transform(row,move))
            def shift(match):
                old = int(match[3])
                if not move or old < 3:return match[0]
                reference_changes.append({"entry":name,"row":number,"before":old,"after":old+1})
                return match[1] + target + f"[{old+1}]" + match[4]
            lines[index] = pair.sub(shift,line)
        updated = "".join(lines)
        after_rows = [json.loads(line) for line in updated.splitlines() if line.strip()]
        assert after_rows == expected_rows
        if name == main_name:
            assert after_rows[:4] == before_rows[:4]
            assert after_rows[4]["CLs"][6]["Var"] == target + "[4]"
        if updated != text:replacements[name] = updated
    for name,text in texts.items():
        if not text.startswith("[SLWD"):
            continue
        match = re.search(r"(?m)^\+\+[^\r\n]*\bN="+re.escape(target)+r"\t[^\r\n]*",text)
        if not match:continue
        old_line = match[0]
        assert "ARRAY[0..99] OF Bool" in old_line
        old_map = comment_map(old_line)
        if not old_map:continue
        shifted_map = {key + (1 if key >= 3 else 0): value for key,value in old_map.items()}
        shifted_map[3] = added_comment
        xml = "<ECs>" + "".join(f'<EC EK="[{key}]" C="{escape(value, {chr(34): "&quot;", chr(13): "&#xD;", chr(10): "&#xA;"})}" />' for key,value in sorted(shifted_map.items())) + "</ECs>"
        new_line = re.sub(r"(?<=\tEC=)[^\t\r\n]*",lambda m:xml,old_line)
        assert comment_map(new_line) == shifted_map
        assert re.sub(r"\tEC=.*", "", old_line) == re.sub(r"\tEC=.*", "", new_line)
        updated = text[:match.start()] + new_line + text[match.end():]
        assert text.replace(old_line,"<対象宣言>",1) == updated.replace(new_line,"<対象宣言>",1)
        replacements[name] = updated
        moved_comments[name] = sum(key >= 3 for key in old_map)
        new_comments[name] = shifted_map
    assert len(replacements) == 4, list(replacements)
    assert len(reference_changes) == 21, len(reference_changes)
    assert sorted(moved_comments.values()) == [3,6]
    with zipfile.ZipFile(staged,"w") as archive:
        archive.comment = comment
        for info in infos:
            raw = original[info.filename]
            if info.filename in replacements:
                raw = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + replacements[info.filename].encode("utf-8")
            archive.writestr(info,raw)
    with zipfile.ZipFile(staged) as archive:
        assert archive.namelist() == list(original) and archive.testzip() is None
        for name in original:
            if name not in replacements:assert archive.read(name) == original[name]
        rows=[json.loads(line) for line in archive.read(main_name).decode("utf-8-sig").splitlines() if line.strip()]
        coils=collections.Counter(int(pattern.fullmatch(c["Var"])[1]) for row in rows for c in row["CLs"] if c.get("__type")=="ST" and pattern.fullmatch(c.get("Var","")))
        assert set(coils)==set(range(1,11))
        assert {key:value for key,value in coils.items() if value>1}=={6:2}
        for name, values in new_comments.items():
            text=archive.read(name).decode("utf-8-sig")
            line=next(line for line in text.splitlines() if f"\tN={target}\t" in line)
            assert comment_map(line)==values
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before_hash
    report={"source":str(source),"destination":str(destination),"staged":str(staged),
            "source_sha256":before_hash,"output_sha256":hashlib.sha256(staged.read_bytes()).hexdigest(),
            "entries":len(original),"changed_entries":list(replacements),
            "reference_changes":reference_changes,"moved_comments":moved_comments,
            "added_comment_for_retained_3":added_comment,"coil_counts":dict(coils),
            "mapping":"上側[3]保持、下側[3]→[4]、旧[4]～[9]→[5]～[10]",
            "existing_findings":["旧[5]二重出力は新[6]二重出力として保持。", "既存の外部変数コメントとグローバルコメントの文言相違は、修正せず各原文を番号と一緒に移動。"],
            "ladder_counts":ladder_counts,"native_validation":None,"app_build_verified":False,"machine_transfer_performed":False}
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("reference_changes","ladder_counts")},ensure_ascii=False))

def publish():
    report=json.loads(report_path.read_text(encoding="utf-8"))
    assert report["native_validation"] and all("PARSE_FAIL=0 MODEL_FAIL=0" in result for result in report["native_validation"].values())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==report["source_sha256"]
    assert hashlib.sha256(staged.read_bytes()).hexdigest()==report["output_sha256"]
    with staged.open("rb") as incoming,destination.open("xb") as outgoing:shutil.copyfileobj(incoming,outgoing)
    assert hashlib.sha256(destination.read_bytes()).hexdigest()==report["output_sha256"]
    note="\n".join([
        "ST4_A_Rev1_Mの下側[3]から番号を繰り下げ（A→B）",
        "上側の位置4ストッパー戻[3]は保持。下側データ転送[3]→[4]、旧[4]～[9]→[5]～[10]。",
        "自己保持・後続工程・エラー判定の対象参照21か所と、配列要素コメント9件を移動。",
        "残した[3]には既存行コメント「"+report["added_comment_for_retained_3"]+"」を設定。",
        "命令・コイルのRS属性・結線・配置・I/O割付・データ型・他の変数は変更なし。",
        "注意：旧[5]にも元から二重出力があり、新[6]の二重出力として残しています。",
        "注意：既存の外部変数/グローバル要素コメントの文言相違は原文を保持して移動しています。",
        "同梱の読込み処理で全ラダー検査済み。Sysmac画面表示・全体ビルド・実機動作は未確認。転送なし。",
        "原本A版は保持。B版を再インポートして差分と全体ビルドを確認してください。",
    ])+"\n"
    destination.with_suffix(".変更内容.txt").write_text(note,encoding="utf-8-sig")
    print("保存完了",destination)

if __name__=="__main__":
    publish() if "--publish" in sys.argv else build()
