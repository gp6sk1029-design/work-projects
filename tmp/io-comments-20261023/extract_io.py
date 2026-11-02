"""保存済みSysmacから実割付のX/Yコメントだけを読み取る。"""
from pathlib import Path
import collections
import hashlib
import json
import re
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent
revision = sys.argv[1] if len(sys.argv) > 1 else "C"
assert re.fullmatch(r"[A-Z]", revision)
source = next(Path(r"C:\Users\SEIGI-N13\Desktop").glob(f"*20261023{revision}.smc2"))
before = hashlib.sha256(source.read_bytes()).hexdigest()
with zipfile.ZipFile(source) as archive:
    name = next(n for n in archive.namelist() if n.endswith("f07dd06c-505c-431b-b9fc-098949805b4e.xml"))
    text = archive.read(name).decode("utf-8-sig")

def shorten(comment):
    # 入出力番号は別欄に置き、左右や動作方向は消さない。
    value = re.sub(r"[【\[]([XY]\d+)[】\]]", "", comment).strip()
    for old, new in [
        ("A(左側)", "A"), ("B(右側)", "B"),
        ("オリエンタルモータ", "モータ"), ("ピックアップ", "ピック"),
        ("ストッパー", "ストッパ"), ("コンベア", "CV"),
        ("シグナルタワー", "タワー"), ("フォルダターン", "フォルダ回転"),
        ("タッチパネル", "タッチ"),
    ]:
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value).strip(" ：:")

rows = []
unassigned = []
for line in text.splitlines():
    if not line.startswith("++"):
        continue
    item = dict(part.split("=", 1) for part in line[2:].split("\t") if "=" in part)
    match = re.search(r"[【\[]([XY]\d+)[】\]]", item.get("Com", ""))
    if not match:
        continue
    if item.get("AT"):
        assert item["D"].upper() == "BOOL", item
        target = rows
    elif (item.get("D", "").upper() == "BOOL" and item.get("N", "").startswith(("In_", "Out_"))
          and not re.search(r"_(Auto|Manual|Origin|Done)$", item["N"])):
        target = unassigned
    else:
        continue
    target.append({"io": match[1], "short": shorten(item["Com"]),
                   "variable": item["N"], "original": item["Com"], "assignment": item.get("AT", "")})

rows.sort(key=lambda r: (r["io"][0], int(r["io"][1:])))
counts = collections.Counter(r["io"][0] for r in rows)
assert len(set(r["io"] for r in rows)) == len(rows)
if revision == "C":
    assert counts == {"X": 171, "Y": 105}, counts
elif revision == "E":
    assert counts == {"X": 167, "Y": 99} and len(unassigned) == 11, (counts, len(unassigned))
assert all(r["short"] and len(r["short"]) <= len(r["original"]) for r in rows)
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
unassigned.sort(key=lambda r: (r["io"][0], int(r["io"][1:])))
result = {"source": str(source), "sha256": before, "revision": revision,
          "scope": f"保存済み{revision}版。割付済みX/Yを一覧化し、番号付き未割付BOOLは別シートへ。内部変数・番号のない通信データ・空き端子は除外。",
          "counts": dict(counts), "rows": rows, "unassigned": unassigned}
(root / f"io_data_{revision}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"counts": dict(counts), "max_short_length": max(len(r["short"]) for r in rows),
                  "source_sha256": before}, ensure_ascii=False))
