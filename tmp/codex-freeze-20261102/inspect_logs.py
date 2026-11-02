"""本日のローカルログから関連箇所を短く抽出し、本文や認証値の出力を避ける。"""
from pathlib import Path
from collections import Counter
import json
import re

base = Path(r"C:\Users\SEIGI-N13\AppData\Local\Codex\Logs\2026\11\02")
patterns = {
    "画面停止": re.compile(r"unresponsive|render.process.gone|renderer.*crash|out.of.memory|heap limit|fatal", re.I),
    "ブック表示": re.compile(r"\.xlsx|spreadsheet.*(?:error|fail)|artifact.*(?:error|fail)|preview.*(?:error|fail)|workbook.*(?:error|fail)", re.I),
    "通信待ち": re.compile(r"outcome=timeout|websocket.*(?:error|fail|disconnect)|connection.*(?:closed|lost)|failed to fetch", re.I),
}
result = []
for p in sorted(base.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:14]:
    hits = []
    counts = Counter()
    for no, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for kind, pat in patterns.items():
            if pat.search(line):
                counts[kind] += 1
                # ログの先頭、分類、所要時間だけを基本情報とする。
                prefix = line[:min(300, len(line))]
                prefix = re.sub(r"https?://\S+", "[URL省略]", prefix)
                prefix = re.sub(r"(?:token|authorization|cookie|key)=[^ ]+", "[認証値省略]", prefix, flags=re.I)
                hits.append({"line": no, "category": kind, "prefix": prefix, "durationMs": re.findall(r"durationMs=([\d.]+)", line)[:1]})
    if hits:
        result.append({"file": p.name, "counts": dict(counts), "hits": hits[-12:]})
Path(__file__).with_name("log_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
