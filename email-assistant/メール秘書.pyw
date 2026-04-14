#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メール秘書
・自動下書き（ON/OFF）
・キーワード管理
"""

import datetime as _dt
import email.utils as _email_utils
import json
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import ctypes
import ctypes.wintypes

# Windows 11 DPIスケーリング問題を回避
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

BASE_DIR      = Path(__file__).parent
KEYWORDS_FILE = BASE_DIR / "keywords.json"
STYLE_FILE    = BASE_DIR / "style_profile.json"
SCRIPT_FILE   = BASE_DIR / "auto_draft.py"

# auto_draft.py から必要な関数・定数をインポート
sys.path.insert(0, str(BASE_DIR))
from auto_draft import (  # noqa: E402
    _iter_inbox, get_effective_msg, decode_header, get_body,
    generate_reply, write_draft, _restart_thunderbird,
    get_thread_simple, INBOX_PATHS,
)

# 手動下書きタブ用フォルダマップ（表示名 → Path）
MANUAL_FOLDER_MAP = {
    "受信トレイ":   INBOX_PATHS[0],
    "社外":        INBOX_PATHS[1],
    "海外":        INBOX_PATHS[2],
    "生産技術部":   INBOX_PATHS[3],
}

# ── カラーパレット ───────────────────────────────────────────
BG       = "#1e1e2e"
SURFACE  = "#313244"
ACCENT   = "#89b4fa"
GREEN    = "#a6e3a1"
RED      = "#f38ba8"
YELLOW   = "#f9e2af"
TEXT     = "#cdd6f4"
SUBTEXT  = "#a6adc8"


# ── Windows Job Object（親終了時に子プロセスを自動終了） ────────
def _create_job_object():
    """JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE 付きの JobObject を作成する"""
    try:
        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit",     ctypes.c_int64),
                ("LimitFlags",             ctypes.c_uint32),
                ("MinimumWorkingSetSize",  ctypes.c_size_t),
                ("MaximumWorkingSetSize",  ctypes.c_size_t),
                ("ActiveProcessLimit",     ctypes.c_uint32),
                ("Affinity",              ctypes.c_size_t),
                ("PriorityClass",         ctypes.c_uint32),
                ("SchedulingClass",       ctypes.c_uint32),
            ]
        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(f, ctypes.c_uint64) for f in
                        ("ReadOps","WriteOps","OtherOps","ReadBytes","WriteBytes","OtherBytes")]
        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo",               IO_COUNTERS),
                ("ProcessMemoryLimit",   ctypes.c_size_t),
                ("JobMemoryLimit",       ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed",    ctypes.c_size_t),
            ]
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        k32  = ctypes.windll.kernel32
        job  = k32.CreateJobObjectW(None, None)
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
        return job
    except Exception:
        return None

def _assign_to_job(job, process):
    """プロセスを JobObject に登録する"""
    if not job:
        return
    try:
        ctypes.windll.kernel32.AssignProcessToJobObject(job, int(process._handle))
    except Exception:
        pass

def _kill_orphan_auto_draft():
    """起動時：前回の孤児 auto_draft.py プロセスを終了する"""
    try:
        result = subprocess.run(
            ["wmic", "process", "get", "commandline,processid", "/format:csv"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5
        )
        for line in result.stdout.splitlines():
            if "auto_draft.py" in line:
                parts = line.split(",")
                pid = parts[-1].strip()
                if pid.isdigit():
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    except Exception:
        pass


# ── スタイルJSON ─────────────────────────────────────────────
def load_style() -> dict:
    try:
        with open(STYLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"口調": "", "よく使う表現": [], "避けたい表現": [], "その他の癖・好み": []}

def save_style(data: dict):
    with open(STYLE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── キーワードJSON ───────────────────────────────────────────
def load_kw() -> dict:
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_kw(data: dict):
    with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── メインアプリ ─────────────────────────────────────────────
class MailHisho(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("メール秘書")
        self.geometry("520x720")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._process = None       # 自動下書きプロセス
        self._log_queue = queue.Queue()  # ログ受け取り用キュー
        self._job = None           # Windows Job Object（孤児プロセス防止）
        _kill_orphan_auto_draft()  # 起動時に前回の孤児プロセスを掃除
        self._build_ui()

    # ── UI構築 ───────────────────────────────────────────────
    def _build_ui(self):
        # ヘッダー
        hdr = tk.Frame(self, bg=SURFACE, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📨  メール秘書", font=("Yu Gothic UI", 16, "bold"),
                 bg=SURFACE, fg=TEXT).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="for 一宮電機", font=("Yu Gothic UI", 9),
                 bg=SURFACE, fg=SUBTEXT).pack(side="right", padx=20)

        # タブ
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",        background=BG,      borderwidth=0)
        style.configure("TNotebook.Tab",    background=SURFACE, foreground=TEXT,
                        padding=[14, 8],    font=("Yu Gothic UI", 10))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])
        style.configure("TFrame", background=BG)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        tab1 = ttk.Frame(nb)
        tab2 = ttk.Frame(nb)
        tab3 = ttk.Frame(nb)
        tab4 = ttk.Frame(nb)
        nb.add(tab1, text="  🤖 自動下書き  ")
        nb.add(tab2, text="  🔑 キーワード管理  ")
        nb.add(tab3, text="  ✏️ 文体設定  ")
        nb.add(tab4, text="  📝 手動下書き  ")

        self._build_tab_auto(tab1)
        self._build_tab_kw(tab2)
        self._build_tab_style(tab3)
        self._build_tab_manual(tab4)

    # ── タブ①：自動下書き ────────────────────────────────────
    def _build_tab_auto(self, parent):
        # ステータス表示
        status_frame = tk.Frame(parent, bg=SURFACE, height=100)
        status_frame.pack(fill="x", padx=16, pady=(20, 8))
        status_frame.pack_propagate(False)

        tk.Label(status_frame, text="ステータス", font=("Yu Gothic UI", 9),
                 bg=SURFACE, fg=SUBTEXT).pack(anchor="w", padx=16, pady=(10, 2))

        self.status_dot = tk.Label(status_frame, text="⏹  停止中",
                                   font=("Yu Gothic UI", 14, "bold"),
                                   bg=SURFACE, fg=RED)
        self.status_dot.pack(anchor="w", padx=16)

        # 説明
        desc = (
            "Thunderbirdが起動中のとき、受信から5分以内の\n"
            "新着メールを検出して自動で下書きを作成します。"
        )
        tk.Label(parent, text=desc, font=("Yu Gothic UI", 10),
                 bg=BG, fg=SUBTEXT, justify="left").pack(anchor="w", padx=20, pady=(8, 0))

        # ON/OFFボタン
        self.toggle_btn = tk.Button(
            parent, text="▶  自動下書きを開始",
            font=("Yu Gothic UI", 13, "bold"),
            bg=GREEN, fg=BG, relief="flat",
            padx=20, pady=14, cursor="hand2",
            command=self.toggle_auto
        )
        self.toggle_btn.pack(fill="x", padx=20, pady=16)

        # ログ表示
        tk.Label(parent, text="ログ", font=("Yu Gothic UI", 9),
                 bg=BG, fg=SUBTEXT).pack(anchor="w", padx=20)

        log_frame = tk.Frame(parent, bg=SURFACE)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        sb = tk.Scrollbar(log_frame)
        sb.pack(side="right", fill="y")

        self.log_box = tk.Text(log_frame, yscrollcommand=sb.set,
                               font=("Consolas", 9),
                               bg=SURFACE, fg=TEXT,
                               relief="flat", state="disabled",
                               height=10)
        self.log_box.pack(fill="both", expand=True, padx=4, pady=4)
        sb.config(command=self.log_box.yview)

    def toggle_auto(self):
        if self._process is None or self._process.poll() is not None:
            # 開始：Job Object を作成してから子プロセスを起動
            self._job = _create_job_object()
            self._process = subprocess.Popen(
                [sys.executable, str(SCRIPT_FILE)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            _assign_to_job(self._job, self._process)  # Job Object に登録
            self.status_dot.config(text="▶  稼働中", fg=GREEN)
            self.toggle_btn.config(text="⏹  自動下書きを停止", bg=RED)
            self._log("自動下書きを開始しました。")
            # バックグラウンドスレッドでログを読み取る
            t = threading.Thread(target=self._read_log, daemon=True)
            t.start()
            self._poll_queue()
        else:
            # 停止
            self._process.terminate()
            self._process = None
            self.status_dot.config(text="⏹  停止中", fg=RED)
            self.toggle_btn.config(text="▶  自動下書きを開始", bg=GREEN)
            self._log("自動下書きを停止しました。")

    def _log(self, msg: str):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _read_log(self):
        """バックグラウンドスレッド: プロセスの出力をキューに流す"""
        try:
            for line in self._process.stdout:
                self._log_queue.put(line.rstrip())
        except Exception:
            pass

    def _poll_queue(self):
        """UIスレッド: キューからログを取り出して表示する"""
        try:
            while True:
                line = self._log_queue.get_nowait()
                self._log(line)
        except queue.Empty:
            pass
        if self._process and self._process.poll() is None:
            self.after(300, self._poll_queue)

    # ── タブ②：キーワード管理 ────────────────────────────────
    def _build_tab_kw(self, parent):
        style = ttk.Style()
        style.configure("TNotebook.Inner", background=BG)

        inner_nb = ttk.Notebook(parent)
        inner_nb.pack(fill="both", expand=True, padx=12, pady=12)

        tabs = [
            ("手動キーワード", "kw",     "件名・送信者にこの文字が含まれたらスキップ"),
            ("除外送信者",   "sender", "このアドレスからのメールはスキップ"),
            ("自動学習済み", "learn",  "自動で記録された送信者"),
        ]
        for label, tag, desc in tabs:
            f = ttk.Frame(inner_nb)
            inner_nb.add(f, text=f"  {label}  ")
            self._build_kw_tab(f, tag, desc)

    def _build_kw_tab(self, parent, tag, desc):
        tk.Label(parent, text=desc, font=("Yu Gothic UI", 9),
                 bg=BG, fg=SUBTEXT).pack(anchor="w", padx=8, pady=(8, 4))

        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="both", expand=True, padx=8)

        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")

        lb = tk.Listbox(frame, yscrollcommand=sb.set,
                        font=("Yu Gothic UI", 11),
                        bg=SURFACE, fg=TEXT,
                        selectbackground=ACCENT, selectforeground=BG,
                        relief="flat", highlightthickness=0,
                        activestyle="none", height=9)
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)
        setattr(self, f"lb_{tag}", lb)

        bottom = tk.Frame(parent, bg=BG)
        bottom.pack(fill="x", padx=8, pady=8)

        entry = tk.Entry(bottom, font=("Yu Gothic UI", 11),
                         bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         relief="flat", highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=SURFACE)
        entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 6))
        setattr(self, f"entry_{tag}", entry)

        tk.Button(bottom, text="追加", font=("Yu Gothic UI", 10, "bold"),
                  bg=ACCENT, fg=BG, relief="flat",
                  padx=12, pady=7, cursor="hand2",
                  command=lambda t=tag: self.kw_add(t)).pack(side="left", padx=(0, 4))

        tk.Button(bottom, text="削除", font=("Yu Gothic UI", 10),
                  bg=RED, fg=BG, relief="flat",
                  padx=12, pady=7, cursor="hand2",
                  command=lambda t=tag: self.kw_delete(t)).pack(side="left")

        entry.bind("<Return>", lambda e, t=tag: self.kw_add(t))
        self.kw_refresh(tag)

    def kw_refresh(self, tag):
        lb  = getattr(self, f"lb_{tag}")
        key = {"kw": "手動キーワード", "sender": "除外送信者", "learn": "自動学習"}[tag]
        lb.delete(0, tk.END)
        for item in load_kw().get(key, []):
            lb.insert(tk.END, f"  {item}")

    def kw_add(self, tag):
        entry = getattr(self, f"entry_{tag}")
        value = entry.get().strip()
        if not value:
            return
        key  = {"kw": "手動キーワード", "sender": "除外送信者", "learn": "自動学習"}[tag]
        data = load_kw()
        if value in data[key]:
            messagebox.showinfo("確認", f"「{value}」はすでに登録されています。")
            return
        data[key].append(value)
        save_kw(data)
        entry.delete(0, tk.END)
        self.kw_refresh(tag)

    def kw_delete(self, tag):
        lb    = getattr(self, f"lb_{tag}")
        sel   = lb.curselection()
        if not sel:
            messagebox.showinfo("確認", "削除する項目を選択してください。")
            return
        value = lb.get(sel[0]).strip()
        if not messagebox.askyesno("削除確認", f"「{value}」を削除しますか？"):
            return
        key  = {"kw": "手動キーワード", "sender": "除外送信者", "learn": "自動学習"}[tag]
        data = load_kw()
        if value in data[key]:
            data[key].remove(value)
            save_kw(data)
            self.kw_refresh(tag)

    # ── タブ③：文体設定 ──────────────────────────────────────
    def _build_tab_style(self, parent):
        # 口調（テキスト入力）
        tone_frame = tk.Frame(parent, bg=BG)
        tone_frame.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(tone_frame,
                 text="① 口調・全体スタイル（自由に入力して「口調を保存」）",
                 font=("Yu Gothic UI", 9), bg=BG, fg=SUBTEXT).pack(anchor="w")
        row = tk.Frame(tone_frame, bg=BG)
        row.pack(fill="x", pady=(2, 0))
        self.tone_entry = tk.Entry(row, font=("Yu Gothic UI", 11),
                                   bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                                   relief="flat", highlightthickness=1,
                                   highlightcolor=ACCENT, highlightbackground=SURFACE)
        self.tone_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        tk.Button(row, text="口調を保存", font=("Yu Gothic UI", 10, "bold"),
                  bg=ACCENT, fg=BG, relief="flat", padx=12, pady=6, cursor="hand2",
                  command=self.style_save_tone).pack(side="left")
        self.tone_entry.insert(0, load_style().get("口調", ""))

        tk.Label(parent,
                 text="② 下のタブで表現リストを管理（入力して「追加」ボタン）",
                 font=("Yu Gothic UI", 9), bg=BG, fg=SUBTEXT).pack(anchor="w", padx=12, pady=(8, 0))

        # リスト系タブ（よく使う表現・避けたい・癖）
        inner_nb = ttk.Notebook(parent)
        inner_nb.pack(fill="both", expand=True, padx=12, pady=8)
        style_tabs = [
            ("よく使う表現", "like",   "Geminiがこの表現を積極的に使います"),
            ("避けたい表現", "avoid",  "この表現は使用されなくなります"),
            ("その他の癖・好み", "pref", "文体の傾向や好みを自由に記述"),
        ]
        for label, tag, desc in style_tabs:
            f = ttk.Frame(inner_nb)
            inner_nb.add(f, text=f"  {label}  ")
            self._build_style_tab(f, tag, desc)

    def _build_style_tab(self, parent, tag, desc):
        tk.Label(parent, text=desc, font=("Yu Gothic UI", 9),
                 bg=BG, fg=SUBTEXT).pack(anchor="w", padx=8, pady=(8, 4))

        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="both", expand=True, padx=8)

        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")
        lb = tk.Listbox(frame, yscrollcommand=sb.set,
                        font=("Yu Gothic UI", 11),
                        bg=SURFACE, fg=TEXT,
                        selectbackground=ACCENT, selectforeground=BG,
                        relief="flat", highlightthickness=0,
                        activestyle="none", height=7)
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)
        setattr(self, f"style_lb_{tag}", lb)

        tk.Label(parent, text="↓ ここに追加したい表現を入力してEnterまたは「追加」",
                 font=("Yu Gothic UI", 8), bg=BG, fg=YELLOW).pack(anchor="w", padx=8)
        bottom = tk.Frame(parent, bg=BG)
        bottom.pack(fill="x", padx=8, pady=(2, 8))
        entry = tk.Entry(bottom, font=("Yu Gothic UI", 11),
                         bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         relief="flat", highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=SURFACE)
        entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 6))
        setattr(self, f"style_entry_{tag}", entry)
        tk.Button(bottom, text="追加", font=("Yu Gothic UI", 10, "bold"),
                  bg=ACCENT, fg=BG, relief="flat", padx=12, pady=7, cursor="hand2",
                  command=lambda t=tag: self.style_add(t)).pack(side="left", padx=(0, 4))
        tk.Button(bottom, text="削除", font=("Yu Gothic UI", 10),
                  bg=RED, fg=BG, relief="flat", padx=12, pady=7, cursor="hand2",
                  command=lambda t=tag: self.style_delete(t)).pack(side="left")
        entry.bind("<Return>", lambda e, t=tag: self.style_add(t))
        self.style_refresh(tag)

    def style_refresh(self, tag):
        lb  = getattr(self, f"style_lb_{tag}")
        key = {"like": "よく使う表現", "avoid": "避けたい表現", "pref": "その他の癖・好み"}[tag]
        lb.delete(0, tk.END)
        for item in load_style().get(key, []):
            lb.insert(tk.END, f"  {item}")

    def style_save_tone(self):
        data = load_style()
        data["口調"] = self.tone_entry.get().strip()
        save_style(data)
        messagebox.showinfo("保存完了", "口調・全体スタイルを保存しました。\n次回の下書き生成から反映されます。")

    def style_add(self, tag):
        entry = getattr(self, f"style_entry_{tag}")
        value = entry.get().strip()
        if not value:
            return
        key  = {"like": "よく使う表現", "avoid": "避けたい表現", "pref": "その他の癖・好み"}[tag]
        data = load_style()
        if value in data.get(key, []):
            messagebox.showinfo("確認", f"「{value}」はすでに登録されています。")
            return
        data.setdefault(key, []).append(value)
        save_style(data)
        entry.delete(0, tk.END)
        self.style_refresh(tag)
        messagebox.showinfo("追加完了", f"「{value}」を追加しました。")

    def style_delete(self, tag):
        lb  = getattr(self, f"style_lb_{tag}")
        sel = lb.curselection()
        if not sel:
            messagebox.showinfo("確認", "削除する項目を選択してください。")
            return
        value = lb.get(sel[0]).strip()
        if not messagebox.askyesno("削除確認", f"「{value}」を削除しますか？"):
            return
        key  = {"like": "よく使う表現", "avoid": "避けたい表現", "pref": "その他の癖・好み"}[tag]
        data = load_style()
        if value in data.get(key, []):
            data[key].remove(value)
            save_style(data)
            self.style_refresh(tag)

    # ── タブ④：手動下書き ────────────────────────────────────
    def _build_tab_manual(self, parent):
        self._manual_emails = []

        # フォルダ選択行
        top = tk.Frame(parent, bg=BG)
        top.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(top, text="フォルダ:", font=("Yu Gothic UI", 10),
                 bg=BG, fg=SUBTEXT).pack(side="left", padx=(0, 6))

        self._manual_folder_var = tk.StringVar(value="受信トレイ")
        folder_choices = list(MANUAL_FOLDER_MAP.keys())
        opt = tk.OptionMenu(top, self._manual_folder_var, *folder_choices)
        opt.config(font=("Yu Gothic UI", 10), bg=SURFACE, fg=TEXT,
                   relief="flat", highlightthickness=0,
                   activebackground=ACCENT, activeforeground=BG)
        opt["menu"].config(bg=SURFACE, fg=TEXT, font=("Yu Gothic UI", 10),
                           activebackground=ACCENT, activeforeground=BG)
        opt.pack(side="left", padx=(0, 8))

        tk.Button(top, text="📥 一覧を取得",
                  font=("Yu Gothic UI", 10, "bold"),
                  bg=ACCENT, fg=BG, relief="flat",
                  padx=12, pady=6, cursor="hand2",
                  command=self._manual_load_emails).pack(side="left")

        # メール一覧
        list_frame = tk.Frame(parent, bg=SURFACE)
        list_frame.pack(fill="both", expand=True, padx=12, pady=4)

        sb = tk.Scrollbar(list_frame)
        sb.pack(side="right", fill="y")

        self.manual_lb = tk.Listbox(
            list_frame, yscrollcommand=sb.set,
            font=("Consolas", 9),
            bg=SURFACE, fg=TEXT,
            selectbackground=ACCENT, selectforeground=BG,
            relief="flat", highlightthickness=0,
            activestyle="none", height=11)
        self.manual_lb.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        sb.config(command=self.manual_lb.yview)

        # 下書き作成ボタン（生成中は無効化して多重実行を防ぐ）
        self.manual_create_btn = tk.Button(
            parent, text="📝 この件を下書き作成",
            font=("Yu Gothic UI", 13, "bold"),
            bg=GREEN, fg=BG, relief="flat",
            padx=20, pady=12, cursor="hand2",
            command=self._manual_create_draft)
        self.manual_create_btn.pack(fill="x", padx=12, pady=(8, 4))
        self._manual_creating = False  # 多重実行ガード

        # ステータスラベル
        self.manual_status = tk.Label(
            parent, text="← メールを選択して「下書き作成」",
            font=("Yu Gothic UI", 9),
            bg=BG, fg=SUBTEXT)
        self.manual_status.pack(anchor="w", padx=14)

    def _manual_load_emails(self):
        """選択中フォルダのメール一覧を取得してListboxに表示する"""
        folder_name = self._manual_folder_var.get()
        inbox_path  = MANUAL_FOLDER_MAP[folder_name]

        if not inbox_path.exists():
            messagebox.showerror("エラー", f"フォルダが見つかりません:\n{inbox_path}")
            return

        self.manual_lb.delete(0, tk.END)
        self._manual_emails = []
        self.manual_status.config(text="⏳ 読み込み中...", fg=YELLOW)
        self.update_idletasks()

        try:
            emails = []
            seen_ids = set()  # Message-ID重複除去用

            for _uidl, msg in _iter_inbox(inbox_path):
                real    = get_effective_msg(msg)

                # Fromがない不正メッセージはスキップ
                if not real.get("From") and not real.get("Date"):
                    continue

                # Message-IDで重複除去（mboxの誤分割対策）
                mid = real.get("Message-ID", "").strip()
                if mid:
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)

                subject = decode_header(real.get("Subject", "（件名なし）"))
                sender  = decode_header(real.get("From", "（不明）"))
                date    = decode_header(real.get("Date", ""))

                # 日付をdatetimeに変換（ソート用）
                try:
                    dt = _email_utils.parsedate_to_datetime(date)
                except Exception:
                    dt = None

                emails.append({
                    "msg":     real,
                    "subject": subject,
                    "sender":  sender,
                    "date":    date,
                    "dt":      dt,
                    "path":    inbox_path,
                })

            # 日付降順ソート（日付不明は末尾）→ 最新30件
            _epoch = _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)
            emails.sort(
                key=lambda e: e["dt"] if e["dt"] else _epoch,
                reverse=True)
            emails = emails[:30]
            self._manual_emails = emails

            for e in emails:
                subj_disp   = e["subject"][:28]
                sender_disp = e["sender"][:22]
                date_disp   = e["date"][:16]
                self.manual_lb.insert(
                    tk.END,
                    f"  {subj_disp:<28}  {sender_disp:<22}  {date_disp}")

            self.manual_status.config(
                text=f"✅ {len(emails)} 件取得 — 返信したいメールを選択してください",
                fg=GREEN)

        except Exception as ex:
            self.manual_status.config(text=f"❌ エラー: {ex}", fg=RED)

    def _manual_create_draft(self):
        """選択中のメールに対してGeminiで返信文を生成し下書きに保存する"""
        # 多重実行ガード（生成中に再度押されても無視）
        if self._manual_creating:
            return

        sel = self.manual_lb.curselection()
        if not sel:
            messagebox.showinfo("確認", "返信したいメールを選択してください。")
            return
        if not self._manual_emails:
            messagebox.showinfo("確認", "先に「📥 一覧を取得」を押してください。")
            return

        idx        = sel[0]
        email_data = self._manual_emails[idx]

        # ボタン無効化（生成完了まで押せないようにする）
        self._manual_creating = True
        self.manual_create_btn.config(state="disabled", bg=SURFACE, text="⏳ 生成中...")
        self.manual_status.config(text="⏳ Geminiが返信文を生成中...", fg=YELLOW)
        self.update_idletasks()

        def worker():
            try:
                real        = email_data["msg"]
                subject     = email_data["subject"]
                sender      = email_data["sender"]
                body        = get_body(real)
                sender_addr = _email_utils.parseaddr(real.get("From", ""))[1]
                thread      = get_thread_simple(sender_addr, email_data["path"])
                reply       = generate_reply(subject, sender, body, thread)
                write_draft(subject, sender, reply)

                def on_done():
                    self.manual_status.config(
                        text=f"✅ 下書き保存完了: Re: {subject[:30]}",
                        fg=GREEN)
                    self.manual_create_btn.config(
                        state="normal", bg=GREEN, text="📝 この件を下書き作成")
                    self._manual_creating = False

                self.after(0, on_done)
                self.after(500, _restart_thunderbird)

            except Exception as ex:
                err = str(ex)

                def on_error():
                    self.manual_status.config(text=f"❌ エラー: {err}", fg=RED)
                    self.manual_create_btn.config(
                        state="normal", bg=GREEN, text="📝 この件を下書き作成")
                    self._manual_creating = False

                self.after(0, on_error)

        threading.Thread(target=worker, daemon=True).start()

    def on_close(self):
        if self._process and self._process.poll() is None:
            if messagebox.askyesno("確認", "自動下書きが稼働中です。終了しますか？"):
                self._process.terminate()
                self.destroy()
        else:
            self.destroy()


if __name__ == "__main__":
    import traceback
    _log = BASE_DIR / "startup_error.log"
    try:
        app = MailHisho()
        app.protocol("WM_DELETE_WINDOW", app.on_close)
        app.mainloop()
    except Exception:
        _log.write_text(traceback.format_exc(), encoding="utf-8")
