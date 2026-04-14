#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
キーワード管理スクリプト
返信不要キーワード・除外送信者を手動で追加・削除・一覧表示する

使い方:
  python keyword_manager.py list                        # 一覧表示
  python keyword_manager.py add-keyword "配信停止"      # キーワード追加
  python keyword_manager.py remove-keyword "配信停止"   # キーワード削除
  python keyword_manager.py add-sender "info@foo.com"  # 送信者除外追加
  python keyword_manager.py remove-sender "info@foo.com" # 送信者除外削除
"""

import json
import sys
from pathlib import Path

KEYWORDS_FILE = Path(__file__).parent / "keywords.json"


def load() -> dict:
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data: dict):
    with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("保存しました。")


def cmd_list():
    data = load()
    print("\n【手動キーワード】（件名・送信者に含まれると返信不要と判定）")
    for i, kw in enumerate(data["手動キーワード"], 1):
        print(f"  {i:2}. {kw}")

    print("\n【除外送信者】（このアドレスからのメールはスキップ）")
    senders = data["除外送信者"]
    if senders:
        for i, s in enumerate(senders, 1):
            print(f"  {i:2}. {s}")
    else:
        print("  （登録なし）")

    print("\n【自動学習済み】")
    learned = data["自動学習"]
    if learned:
        for i, s in enumerate(learned, 1):
            print(f"  {i:2}. {s}")
    else:
        print("  （まだ学習データなし）")
    print()


def cmd_add_keyword(keyword: str):
    data = load()
    if keyword in data["手動キーワード"]:
        print(f"「{keyword}」はすでに登録されています。")
        return
    data["手動キーワード"].append(keyword)
    save(data)
    print(f"キーワード「{keyword}」を追加しました。")


def cmd_remove_keyword(keyword: str):
    data = load()
    if keyword not in data["手動キーワード"]:
        print(f"「{keyword}」は登録されていません。")
        return
    data["手動キーワード"].remove(keyword)
    save(data)
    print(f"キーワード「{keyword}」を削除しました。")


def cmd_add_sender(sender: str):
    data = load()
    if sender in data["除外送信者"]:
        print(f"「{sender}」はすでに登録されています。")
        return
    data["除外送信者"].append(sender)
    save(data)
    print(f"除外送信者「{sender}」を追加しました。")


def cmd_remove_sender(sender: str):
    data = load()
    if sender in data["除外送信者"]:
        data["除外送信者"].remove(sender)
        save(data)
        print(f"除外送信者「{sender}」を削除しました。")
    elif sender in data["自動学習"]:
        data["自動学習"].remove(sender)
        save(data)
        print(f"自動学習済み「{sender}」を削除しました。")
    else:
        print(f"「{sender}」は登録されていません。")


def usage():
    print(__doc__)


def main():
    args = sys.argv[1:]

    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "add-keyword" and len(args) == 2:
        cmd_add_keyword(args[1])
    elif args[0] == "remove-keyword" and len(args) == 2:
        cmd_remove_keyword(args[1])
    elif args[0] == "add-sender" and len(args) == 2:
        cmd_add_sender(args[1])
    elif args[0] == "remove-sender" and len(args) == 2:
        cmd_remove_sender(args[1])
    else:
        usage()


if __name__ == "__main__":
    main()
