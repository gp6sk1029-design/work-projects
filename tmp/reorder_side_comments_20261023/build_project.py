"""コメント欄だけの左右表記を移し、E版を作成・検証する。"""
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
source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob("*20261023D.smc2"))
destination = source.with_name(source.name.replace("20261023D", "20261023E"))
staged = base / destination.name
report_path = base / "verification.json"
side = re.compile(r"A\(左側\)|B\(右側\)")
labels = re.compile(r"(【[^】]*】|\[[XY]\d+\])")
changes = []

def reorder_segment(segment):
    match = side.search(segment)
    if not match:
        return segment
    # 行頭記号と先頭空白は保持。すでに左右表記が先頭なら完全に維持。
    lead = re.match(r"[ \t]*(?:\#+[ \t]*|//[ \t]*)?", segment).group(0)
    if match.start() == len(lead):
        return segment
    left = segment[len(lead):match.start()]
    right = segment[match.end():]
    if left.endswith((" ", "\t")) and right.startswith((" ", "\t")):
        right = right.lstrip(" \t")
    body = (left + right).lstrip(" \t")
    return lead + match.group(0) + " " + body

def reorder(value):
    # 一つの行に複数I/O番号がある場合も、番号ごとに処理する。
    pieces = re.split(r"(\r\n|\n|\r)", value)
    for i in range(0, len(pieces), 2):
        chunks = labels.split(pieces[i])
        for j in range(0, len(chunks), 2):
            chunks[j] = reorder_segment(chunks[j])
        pieces[i] = "".join(chunks)
    return "".join(pieces)

def update(value, entry, kind):
    result = reorder(value)
    if result != value:
        assert reorder(result) == result, (value, result)
        assert collections.Counter(side.findall(result)) == collections.Counter(side.findall(value))
        assert labels.findall(result) == labels.findall(value)
        changes.append({"entry": entry, "kind": kind, "before": value, "after": result})
    return result

def xml_attr(text, attr, entry, kind):
    pattern = re.compile(r'(\b' + attr + r'=")([^"\r\n]*)(")')
    def replacement(match):
        value = html.unescape(match[2])
        result = update(value, entry, kind)
        if result == value:
            return match[0]
        encoded = escape(result, {'"': '&quot;', '\r': '&#xD;', '\n': '&#xA;', '\t': '&#x9;'})
        return match[1] + encoded + match[3]
    return pattern.sub(replacement, text)

def without_slwd_comments(text):
    text = re.sub(r"(?m)(\tCom=)[^\t\r\n]*", r"\1", text)
    return re.sub(r'(\bC=")[^"\r\n]*(")', r'\1\2', text)

def without_xml_comments(root):
    root = copy.deepcopy(root)
    for node in root.iter():
        node.attrib.pop("Comment", None)
    return ET.tostring(root, encoding="utf-8")

def without_rung_comments(value):
    if isinstance(value, dict):
        return {k: without_rung_comments(v) for k, v in value.items() if k != "CMT"}
    if isinstance(value, list):
        return [without_rung_comments(v) for v in value]
    return value

def build():
    assert not destination.exists(), f"E版が既存のため停止：{destination}"
    before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    formats = {}
    ladder_counts = {}
    changed_entries = []
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(staged, "w") as result:
        result.comment = original.comment
        for info in original.infolist():
            raw = original.read(info.filename)
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                result.writestr(info, raw)
                continue
            updated = text
            kind = None
            if text.startswith("[SLWD"):
                kind = "SLWD"
                def variable_comment(match):
                    return match[1] + update(match[2], info.filename, "変数コメント")
                updated = re.sub(r"(?m)(\tCom=)([^\t\r\n]*)", variable_comment, text)
                updated = xml_attr(updated, "C", info.filename, "配列要素コメント")
                assert without_slwd_comments(text) == without_slwd_comments(updated)
                for ec in re.findall(r"\tEC=([^\t\r\n]*)", updated):
                    ET.fromstring(ec)
            elif text.lstrip().startswith("{"):
                # ラダーはCMTのみ差し替え、接点・コイル・結線情報を保持する。
                lines = [line for line in text.splitlines() if line.strip()]
                try:
                    rows = [json.loads(line) for line in lines]
                except json.JSONDecodeError:
                    rows = []
                if rows and all(isinstance(row, dict) and "CLs" in row for row in rows):
                    kind = "LADDER"
                    pattern = re.compile(r'("CMT"\s*:\s*)("(?:\\.|[^"\\])*")')
                    def rung_comment(match):
                        value = json.loads(match[2])
                        new = update(value, info.filename, "ラダー行コメント")
                        return match[0] if new == value else match[1] + json.dumps(new, ensure_ascii=False)
                    updated = pattern.sub(rung_comment, text)
                    after_rows = [json.loads(line) for line in updated.splitlines() if line.strip()]
                    assert len(rows) == len(after_rows)
                    assert without_rung_comments(rows) == without_rung_comments(after_rows)
                    ladder_counts[info.filename] = len(rows)
            elif text.lstrip().startswith("<"):
                root = ET.fromstring(text)
                if root.tag == "Variables":
                    kind = "VARIABLE_METADATA"
                    updated = xml_attr(text, "Comment", info.filename, "変数管理コメント")
                    assert without_xml_comments(root) == without_xml_comments(ET.fromstring(updated))
            if updated != text:
                bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
                out = bom + updated.encode("utf-8")
                assert kind in ("SLWD", "LADDER", "VARIABLE_METADATA")
                changed_entries.append(info.filename)
                formats[info.filename] = kind
            else:
                out = raw
            result.writestr(info, out)
    # 保存後に全エントリを再検査する。
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(staged) as result:
        assert original.namelist() == result.namelist()
        assert result.testzip() is None
        for name in original.namelist():
            old, new = original.read(name), result.read(name)
            if name not in changed_entries:
                assert old == new
                continue
            before, after = old.decode("utf-8-sig"), new.decode("utf-8-sig")
            if formats[name] == "SLWD":
                assert without_slwd_comments(before) == without_slwd_comments(after)
                for line in after.splitlines():
                    if line.startswith("++"):
                        item = dict(x.split("=", 1) for x in line[2:].split("\t") if "=" in x)
                        if "Com" in item: assert reorder(item["Com"]) == item["Com"]
                        if "EC" in item:
                            for ec in ET.fromstring(item["EC"]).iter("EC"):
                                assert reorder(ec.get("C", "")) == ec.get("C", "")
            elif formats[name] == "VARIABLE_METADATA":
                for node in ET.fromstring(after).iter("Variable"):
                    assert reorder(node.get("Comment", "")) == node.get("Comment", "")
            elif formats[name] == "LADDER":
                for line in after.splitlines():
                    if line.strip():
                        value = json.loads(line).get("CMT", "")
                        assert reorder(value) == value
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before_hash
    report = {"source": str(source), "destination": str(destination), "staged": str(staged),
              "source_sha256": before_hash, "output_sha256": hashlib.sha256(staged.read_bytes()).hexdigest(),
              "entries": len(original.namelist()), "changed_entries": changed_entries,
              "counts": dict(collections.Counter(c["kind"] for c in changes)),
              "changed_comment_fields": len(changes), "changes": changes,
              "ladder_counts": ladder_counts, "native_validation": None,
              "logic_variables_types_and_assignments_unchanged": True,
              "hmi_and_binary_entries_unchanged": True}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("changes", "ladder_counts", "changed_entries")}, ensure_ascii=False))
    for change in changes[:8]: print(change["kind"],repr(change["before"]),"=>",repr(change["after"]))

def publish():
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.get("native_validation") is not None, "メーカー変換確認前の公開を禁止"
    assert all("PARSE_FAIL=0 MODEL_FAIL=0" in v for v in report["native_validation"].values())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == report["source_sha256"]
    assert hashlib.sha256(staged.read_bytes()).hexdigest() == report["output_sha256"]
    with staged.open("rb") as incoming, destination.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == report["output_sha256"]
    print("保存完了",destination)

if __name__ == "__main__":
    # 既存順維持、番号維持、左右位置、複数番号、行頭記号を確認。
    tests = {
        "【X214】ストックフォルダA(左側)IN": "【X214】A(左側) ストックフォルダIN",
        "【X414】ストックフォルダB(右側)IN": "【X414】B(右側) ストックフォルダIN",
        "【Y710】A(左側)ST4 反転1ピックアップ戻": "【Y710】A(左側)ST4 反転1ピックアップ戻",
        "自動【Y616】供給A(左側)スライド戻：": "自動【Y616】A(左側) 供給スライド戻：",
        "#検査ユニット：A(左側)ワークセンサ": "#A(左側) 検査ユニット：ワークセンサ",
        "【X201】アキュームA(左側)CV着：有 【X202】A(左側)ワーク位置0：無":
        "【X201】A(左側) アキュームCV着：有 【X202】A(左側)ワーク位置0：無",
    }
    for before, after in tests.items(): assert reorder(before) == after, (before, reorder(before))
    publish() if "--publish" in sys.argv else build()
