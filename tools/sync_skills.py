# -*- coding: utf-8 -*-
"""スキルを .claude/skills から .agents/skills へ同期する（Codex等でも同じ内容を使うため）。

Claude Code は `.claude/skills/`、他のエージェント（Codex等）は `AGENTS.md` と
`.agents/skills/` を見るため、実体を二重に持つ必要がある。
手で写すと必ずズレるので、このスクリプトで一方向ミラーする。

使い方:
    python tools/sync_skills.py            # 差分を表示して同期
    python tools/sync_skills.py --check    # 差分の確認だけ（同期しない）
"""
import sys, os, shutil, filecmp, argparse

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".claude", "skills")
DST = os.path.join(ROOT, ".agents", "skills")


# 同期しないもの（実行時にできる生成物。写すとゴミがリポジトリに残る）
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints"}
SKIP_EXTS = {".pyc", ".pyo"}


def walk(base):
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in SKIP_EXTS:
                continue
            full = os.path.join(dirpath, f)
            yield os.path.relpath(full, base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(SRC):
        print("NG: スキル元フォルダがありません:", SRC)
        return 1

    src_files = sorted(walk(SRC))
    dst_files = sorted(walk(DST)) if os.path.isdir(DST) else []

    add = [f for f in src_files if f not in dst_files]
    rm = [f for f in dst_files if f not in src_files]
    diff = [f for f in src_files if f in dst_files
            and not filecmp.cmp(os.path.join(SRC, f), os.path.join(DST, f), shallow=False)]

    print(f"元: {SRC}\n先: {DST}")
    print(f"  新規 {len(add)}件 / 更新 {len(diff)}件 / 余分 {len(rm)}件")
    for f in add:
        print("   ＋", f)
    for f in diff:
        print("   ↻", f)
    for f in rm:
        print("   －", f, "（元に無いので削除）")

    if a.check:
        ok = not (add or diff or rm)
        print("\n" + ("✅ 同期済みです" if ok else "★ 未同期です。--check なしで実行してください"))
        return 0 if ok else 1

    if not (add or diff or rm):
        print("\n✅ 差分なし（同期済み）")
        return 0

    for f in add + diff:
        s, d = os.path.join(SRC, f), os.path.join(DST, f)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
    for f in rm:
        os.remove(os.path.join(DST, f))
    # 空になったフォルダを掃除
    for dirpath, dirs, files in os.walk(DST, topdown=False):
        if not dirs and not files:
            os.rmdir(dirpath)

    print(f"\n✅ 同期しました（{len(add)+len(diff)}件コピー / {len(rm)}件削除）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
