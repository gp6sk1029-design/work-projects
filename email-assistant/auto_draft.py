#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メール自動下書き生成スクリプト
・Thunderbird起動中のみ動作
・受信から5分以内の新着メールのみ対象
・迷惑メール・メルマガを除外
・Gemini APIで返信文を生成してDrafts mboxに保存
・60秒ごとに繰り返す常駐型
"""

import mailbox
import email as stdlib_email
import json
import os
import re
import email
import email.header
import email.utils
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Windows環境でのエンコードエラーを防ぐ
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 設定 ────────────────────────────────────────────────────
THUNDERBIRD_MAIL_DIR = Path(r"C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp")
DRAFTS_PATH          = THUNDERBIRD_MAIL_DIR / "Drafts"

# 監視するフォルダ
INBOX_PATHS = [
    THUNDERBIRD_MAIL_DIR / "Inbox",
    THUNDERBIRD_MAIL_DIR / "Inbox.sbd" / "1_社内.sbd" / "他部署.sbd" / "2_社外",
    THUNDERBIRD_MAIL_DIR / "Inbox.sbd" / "1_社内.sbd" / "他部署.sbd" / "3_海外",
    THUNDERBIRD_MAIL_DIR / "Inbox.sbd" / "1_社内.sbd" / "生産技術部",  # 大容量→末尾読み
]
LAST_PROCESSED_FILE  = Path(__file__).parent / "last_processed.json"
LOG_DIR              = Path(__file__).parent / "logs"

MY_EMAIL       = os.getenv("MY_EMAIL", "sy-kouda@ime-group.co.jp")
MY_NAME        = os.getenv("MY_NAME", "幸田")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

RECENT_MINUTES        = 35              # 受信から何分以内を対象にするか
LOOP_INTERVAL         = 1800            # 何秒ごとにチェックするか（30分）
KEYWORDS_FILE         = Path(__file__).parent / "keywords.json"
STYLE_FILE            = Path(__file__).parent / "style_profile.json"
SENT_PATH             = THUNDERBIRD_MAIL_DIR / "Sent"
LARGE_FILE_THRESHOLD  = 50 * 1024 * 1024   # 50MB超は末尾読みモードに切り替え
TAIL_SCAN_BYTES       = 5  * 1024 * 1024   # 末尾5MBだけ読む
STYLE_SAMPLE_MAX = 5    # 送信済みメールから取得するサンプル数


def get_effective_msg(msg):
    """Thunderbird POP3形式のmsgを正しく解析して返す。
    >>Fromによりヘッダーが本文扱いになっている場合に再パースする。"""
    if msg.get("From") or msg.get("Date"):
        return msg
    payload = msg.get_payload()
    if not isinstance(payload, str):
        return msg
    # mailboxが>Fromに変換した行を探し、その後ろを再パース
    lines = payload.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if re.match(r">+From ", line):
            remaining = "".join(lines[i + 1:])
            return stdlib_email.message_from_string(remaining)
    return msg


def load_style_profile() -> dict:
    """style_profile.jsonから文体・署名設定を読み込む"""
    try:
        with open(STYLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_sent_samples() -> list[str]:
    """送信済みフォルダから自分のメール本文を最大STYLE_SAMPLE_MAX件取得する"""
    if not SENT_PATH.exists():
        return []
    samples = []
    try:
        inbox = mailbox.mbox(str(SENT_PATH))
        keys  = list(inbox.keys())
        # 末尾（最新）から走査
        for key in reversed(keys):
            if len(samples) >= STYLE_SAMPLE_MAX:
                break
            msg      = inbox[key]
            real_msg = get_effective_msg(msg)
            if MY_EMAIL not in real_msg.get("From", ""):
                continue
            body = get_body(real_msg).strip()
            if len(body) < 30:
                continue
            samples.append(body[:400])
        inbox.close()
    except Exception:
        pass
    return samples


def load_keywords() -> tuple[list, list]:
    """keywords.jsonからキーワードと除外送信者を読み込む"""
    try:
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        patterns = data.get("手動キーワード", []) + data.get("自動学習", [])
        senders  = data.get("除外送信者", [])
        return patterns, senders
    except Exception:
        return [], []


def add_to_learned(sender_email: str):
    """返信不要だった送信者を自動学習に追加する"""
    try:
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if sender_email not in data["自動学習"] and sender_email not in data["除外送信者"]:
            data["自動学習"].append(sender_email)
            with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── ユーティリティ ───────────────────────────────────────────

def decode_header(header_str: str) -> str:
    """メールヘッダーをデコードして文字列で返す"""
    if not header_str:
        return ""
    parts = email.header.decode_header(header_str)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            charset = charset or "utf-8"
            result.append(part.decode(charset, errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def get_body(msg) -> str:
    """メール本文を取得（最大3000文字）"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                try:
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body[:3000]


# ── Thunderbird起動確認 ──────────────────────────────────────

def is_thunderbird_running() -> bool:
    """Thunderbirdプロセスが起動中か確認する"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq thunderbird.exe"],
            capture_output=True, text=True
        )
        return "thunderbird.exe" in result.stdout.lower()
    except Exception:
        return False


# ── 受信時刻確認 ────────────────────────────────────────────

def is_recent(msg, minutes: int = RECENT_MINUTES) -> bool:
    """受信日時が指定分以内かどうか判定する（Receivedヘッダーを優先）"""
    now = datetime.now(timezone.utc)

    # Receivedヘッダーから受信時刻を取得（最初の1行を使用）
    received = msg.get("Received", "")
    if received:
        # ";" の後ろに日時が書かれている形式
        parts = received.split(";")
        if len(parts) >= 2:
            date_str = parts[-1].strip()
            try:
                dt = email.utils.parsedate_to_datetime(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return (now - dt) <= timedelta(minutes=minutes)
            except Exception:
                pass

    # フォールバック：Dateヘッダーを使用
    date_str = msg.get("Date", "")
    if date_str:
        try:
            dt = email.utils.parsedate_to_datetime(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (now - dt) <= timedelta(minutes=minutes)
        except Exception:
            pass

    return False


# ── 迷惑メール・返信不要判定 ────────────────────────────────

def needs_reply(msg) -> bool:
    """返信が必要なメールかどうか判定する（Trueなら返信必要）"""
    sender      = decode_header(msg.get("From", ""))
    subject     = decode_header(msg.get("Subject", ""))
    sender_addr = email.utils.parseaddr(sender)[1].lower()

    # X-Spam-Statusヘッダー確認
    if "Yes" in msg.get("X-Spam-Status", ""):
        return False

    # Junkフラグ確認
    if msg.get("X-Mozilla-Status", "") == "0100":
        return False

    # keywords.jsonからキーワード・除外送信者を読み込んで判定
    patterns, excluded_senders = load_keywords()

    # 除外送信者チェック
    for excl in excluded_senders:
        if excl.lower() in sender_addr:
            return False

    # キーワードチェック（件名・送信者）
    check = (sender + " " + subject).lower()
    for pattern in patterns:
        if re.search(pattern, check, re.IGNORECASE):
            return False

    return True


# ── 大容量mbox末尾読み ───────────────────────────────────────

def _iter_tail_messages(inbox_path: Path):
    """mboxファイルの末尾TAIL_SCAN_BYTESだけ読んでメッセージをイテレートする。
    新着メールはmboxの末尾に追記されるため、末尾読みで十分。"""
    with open(inbox_path, "rb") as f:
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(max(0, file_size - TAIL_SCAN_BYTES))
        tail_data = f.read()

    # mbox の From_ 行は必ず「From 送信者 曜日3文字 ...」の形式
    # 本文中の "From " 行（引用・転送）と区別するため曜日パターンで厳格に判定する
    # 例: From sender@example.com Mon Mar 15 12:00:00 2024
    FROM_LINE = rb'\nFrom \S+ (?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) '

    # 最初の正規 From_ 行を探して断片を除去
    m = re.search(FROM_LINE, b'\n' + tail_data)
    if not m:
        # フォールバック：緩いパターンで再試行
        m = re.search(rb'(?:^|\n)(From [^\n]+\n)', tail_data)
        if not m:
            return
        tail_data = tail_data[m.start(1):]
    else:
        # b'\n' を先頭に付けて検索したので start を 1 ずらす
        start = m.start()  # \n の位置
        tail_data = tail_data[max(0, start - 1):]  # \nを除いた先頭から

    # 正規 From_ パターンで分割（本文中の From は誤判定しない）
    parts = re.split(FROM_LINE, tail_data)
    for i, raw in enumerate(parts):
        if not raw:
            continue
        # 分割後の各パートに From_ ヘッダーを補う
        if not raw.startswith(b'From '):
            raw = b'From UNKNOWN Mon Jan  1 00:00:00 2000\n' + raw
        try:
            yield stdlib_email.message_from_bytes(raw)
        except Exception:
            continue


def _iter_inbox(inbox_path: Path):
    """mboxファイルから (uidl, msg) をイテレートする。
    50MB超の大容量ファイルは末尾のみ読む高速モードを使用する。"""
    file_size = inbox_path.stat().st_size
    folder    = inbox_path.name

    if file_size > LARGE_FILE_THRESHOLD:
        log(f"  大容量フォルダ検出（{file_size // 1024 // 1024}MB）: 末尾{TAIL_SCAN_BYTES // 1024 // 1024}MBのみスキャン")
        for msg in _iter_tail_messages(inbox_path):
            mid  = msg.get("Message-ID", "") or msg.get("X-UIDL", "")
            uidl = f"{folder}:{mid or id(msg)}"
            yield uidl, msg
    else:
        inbox = mailbox.mbox(str(inbox_path))
        try:
            for key in inbox.keys():
                msg  = inbox[key]
                uidl = f"{folder}:{msg.get('X-UIDL', str(key))}"
                yield uidl, msg
        finally:
            inbox.close()


# ── 処理済み管理 ────────────────────────────────────────────

def load_processed() -> set:
    if LAST_PROCESSED_FILE.exists():
        with open(LAST_PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_processed(processed: set):
    with open(LAST_PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed), f, ensure_ascii=False, indent=2)


# ── 過去のやり取り取得 ───────────────────────────────────────

def get_past_thread(sender_email: str, inbox: mailbox.mbox, inbox_path: Path) -> list:
    """送信者との過去のやり取りを直近5件取得"""
    thread = []
    for key in inbox.keys():
        msg = inbox[key]
        real = get_effective_msg(msg)
        msg_from = real.get("From", "")
        msg_to   = real.get("To", "")
        if sender_email in msg_from or sender_email in msg_to:
            thread.append({
                "date":    decode_header(real.get("Date", "")),
                "from":    decode_header(real.get("From", "")),
                "subject": decode_header(real.get("Subject", "")),
                "body":    get_body(real)[:500],
            })
    return thread[-5:]


def get_thread_simple(sender_email: str, inbox_path: Path) -> list:
    """指定フォルダから送信者との過去スレッドを取得（手動下書き用）。
    パスだけ渡せば動くシンプル版。大容量フォルダは末尾読みを使用する。"""
    thread = []
    if not inbox_path.exists():
        return thread
    file_size = inbox_path.stat().st_size
    try:
        if file_size > LARGE_FILE_THRESHOLD:
            msgs = list(_iter_tail_messages(inbox_path))
        else:
            mbox = mailbox.mbox(str(inbox_path))
            msgs = [mbox[k] for k in mbox.keys()]
            mbox.close()
        for msg in msgs:
            real = get_effective_msg(msg)
            msg_from = real.get("From", "")
            msg_to   = real.get("To", "")
            if sender_email in msg_from or sender_email in msg_to:
                thread.append({
                    "date":    decode_header(real.get("Date", "")),
                    "from":    decode_header(real.get("From", "")),
                    "subject": decode_header(real.get("Subject", "")),
                    "body":    get_body(real)[:500],
                })
    except Exception:
        pass
    return thread[-5:]


# ── Gemini APIで返信文生成 ───────────────────────────────────

def generate_reply(subject: str, sender: str, body: str, thread: list) -> str:
    client  = genai.Client(api_key=GEMINI_API_KEY)
    profile = load_style_profile()
    samples = get_sent_samples()

    # ── 文体プロファイル情報を組み立て ──
    style_text = ""
    if profile:
        style_text += "\n\n【送信者の文体・好み（必ず反映すること）】\n"
        if profile.get("口調"):
            style_text += f"口調: {profile['口調']}\n"
        if profile.get("よく使う表現"):
            style_text += "よく使う表現:\n"
            for expr in profile["よく使う表現"]:
                style_text += f"  ・{expr}\n"
        if profile.get("避けたい表現"):
            style_text += "避けたい表現（使用禁止）:\n"
            for expr in profile["避けたい表現"]:
                style_text += f"  ・{expr}\n"
        if profile.get("その他の癖・好み"):
            style_text += "その他の癖・好み:\n"
            for pref in profile["その他の癖・好み"]:
                style_text += f"  ・{pref}\n"

    # ── 送信済みメールの文体サンプル ──
    sample_text = ""
    if samples:
        sample_text = "\n\n【実際の送信メールサンプル（この文体を真似して書くこと）】\n"
        for i, s in enumerate(samples, 1):
            sample_text += f"--- サンプル{i} ---\n{s}\n"

    # ── 過去のやり取り ──
    thread_text = ""
    if thread:
        thread_text = "\n\n【過去のやり取り（直近5件）】\n"
        for t in thread:
            thread_text += (
                f"日付: {t['date']}\n"
                f"送信者: {t['from']}\n"
                f"件名: {t['subject']}\n"
                f"本文: {t['body']}\n---\n"
            )

    prompt = f"""あなたはビジネスメールの返信文を作成するアシスタントです。
以下のメールに対する返信文を日本語で作成してください。
{style_text}{sample_text}
【受信メール情報】
件名: {subject}
送信者: {sender}
本文:
{body}
{thread_text}

【返信文の要件】
- 上記の文体サンプルや好みを忠実に反映した文体・言い回しで書く
- 受領確認・お礼・適切な対応を含める
- 署名は不要（本文のみ）
- 簡潔にまとめる（長すぎない）

返信文のみを出力してください。説明文は不要です。"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return _clean_reply(response.text)


def _clean_reply(text: str) -> str:
    """Geminiの返信文から先頭の「件名：〜」行と余分な空行を除去する"""
    lines = text.splitlines()
    # 先頭から「件名：」「件名:」で始まる行を除去
    while lines and re.match(r'^件名[：:].+', lines[0].strip()):
        lines.pop(0)
    # 除去後の先頭の空行も除去
    while lines and lines[0].strip() == '':
        lines.pop(0)
    return '\n'.join(lines)


# ── 下書き保存 ──────────────────────────────────────────────

def _restart_thunderbird():
    """Thunderbirdを再起動して下書きmboxの変更を反映させる"""
    tb_candidates = [
        r"C:\Program Files\Mozilla Thunderbird\thunderbird.exe",
        r"C:\Program Files (x86)\Mozilla Thunderbird\thunderbird.exe",
    ]
    tb_exe = next((p for p in tb_candidates if os.path.exists(p)), None)

    # Thunderbirdを終了（強制ではなく通常終了）
    subprocess.run(["taskkill", "/IM", "thunderbird.exe"], capture_output=True)
    time.sleep(4)  # 終了を待つ

    # .msfを削除（インデックス再構築のため）
    msf_path = str(DRAFTS_PATH) + ".msf"
    if os.path.exists(msf_path):
        try:
            os.remove(msf_path)
        except Exception:
            pass

    # Thunderbirdを再起動
    if tb_exe:
        subprocess.Popen([tb_exe])
        log("  Thunderbirdを再起動しました（下書き反映のため）")
    else:
        log("  ※Thunderbirdのパスが見つかりません。手動で再起動してください。")


def write_draft(subject: str, sender: str, reply_body: str):
    """ThunderbirdのDrafts mboxに下書きを書き込む"""
    now           = datetime.now()
    date_str      = email.utils.formatdate(localtime=True)
    reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject

    # SubjectをMIMEエンコード（日本語が文字化けしないよう RFC 2047 準拠）
    encoded_subject = email.header.Header(reply_subject, "utf-8").encode()

    # X-Mozilla-Status: 0x0000 = 未読・削除なし（新規下書きとして表示される）
    # ※ 0x0008 は Expunged（削除済み）フラグなので使わない
    # X-Mozilla-Draft-Info が必須（これがないと Thunderbird が下書きと認識しない）
    draft = (
        f"From - {now.strftime('%a %b %d %H:%M:%S %Y')}\n"
        f"X-Mozilla-Status: 0000\n"
        f"X-Mozilla-Status2: 00000000\n"
        f"X-Mozilla-Keys:\n"
        f"X-Mozilla-Draft-Info: internal/draft; vcard=0; receipt=0; DSN=0; uuencode=0; attachmentreminder=0; deliveryformat=0\n"
        f"Date: {date_str}\n"
        f"From: {MY_NAME} <{MY_EMAIL}>\n"
        f"To: {sender}\n"
        f"Subject: {encoded_subject}\n"
        f"MIME-Version: 1.0\n"
        f"Content-Type: text/plain; charset=\"UTF-8\"\n"
        f"Content-Transfer-Encoding: 8bit\n"
        f"\n"
        f"{reply_body}\n"
        f"\n"
    )

    with open(DRAFTS_PATH, "a", encoding="utf-8", newline="\n") as f:
        f.write(draft)


# ── ログ出力 ─────────────────────────────────────────────────

def log(msg: str):
    LOG_DIR.mkdir(exist_ok=True)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── 1回分のチェック処理 ──────────────────────────────────────

def check_folder(inbox_path: Path, processed: set) -> int:
    """指定フォルダをチェックして新着メールの下書きを生成する。作成件数を返す。
    50MB超の大容量フォルダは末尾読みモードで高速処理する。"""
    if not inbox_path.exists():
        return 0

    new_count = 0

    for uidl, msg in _iter_inbox(inbox_path):
        # 処理済みはスキップ
        if uidl in processed:
            continue

        # Thunderbird POP3形式の>>From問題を修正して再パース
        real_msg = get_effective_msg(msg)

        # Fromがないものはスキップ
        sender_raw = real_msg.get("From", "")
        if not sender_raw:
            processed.add(uidl)
            continue

        # 自分が送信したメールはスキップ
        if MY_EMAIL in sender_raw:
            processed.add(uidl)
            continue

        # 受信から35分以内でないものはスキップ（古いメールを無視）
        if not is_recent(real_msg, RECENT_MINUTES):
            processed.add(uidl)
            continue

        # 返信不要（迷惑・メルマガ・自動送信）はスキップ
        if not needs_reply(real_msg):
            subject = decode_header(real_msg.get("Subject", ""))
            log(f"  スキップ（返信不要）: {subject}")
            processed.add(uidl)
            continue

        subject      = decode_header(real_msg.get("Subject", "（件名なし）"))
        sender       = decode_header(sender_raw)
        body         = get_body(real_msg)
        sender_email = email.utils.parseaddr(sender_raw)[1]

        log(f"  新着メール検出 [{inbox_path.name}]: {subject} / {sender}")

        # Gemini APIで返信文生成 → 下書き保存
        try:
            reply = generate_reply(subject, sender, body, [])
            write_draft(subject, sender, reply)
            log(f"  下書き保存完了: {subject}")
            new_count += 1
        except Exception as e:
            log(f"  エラー（{subject}）: {e}")

        processed.add(uidl)

    return new_count


def check_once(processed: set) -> int:
    """全監視フォルダをチェックして新着メールの下書きを生成する。作成件数を返す"""
    total = 0
    for inbox_path in INBOX_PATHS:
        total += check_folder(inbox_path, processed)
    return total


# ── メイン（60秒ループ） ─────────────────────────────────────

def main():
    if not GEMINI_API_KEY:
        log("エラー: GEMINI_API_KEY が設定されていません。.envファイルを確認してください。")
        return

    log("メール自動下書きスクリプト 起動")
    processed = load_processed()

    while True:
        # Thunderbird起動確認
        if not is_thunderbird_running():
            log("  Thunderbird未起動 - 60秒後に再確認")
            time.sleep(LOOP_INTERVAL)
            continue

        # メールチェック
        log("メールチェック開始")
        try:
            count = check_once(processed)
            save_processed(processed)
            log(f"完了 - 新規下書き {count} 件作成")
            # 下書きが1件以上あった場合のみThunderbirdを再起動（まとめて1回）
            if count > 0:
                _restart_thunderbird()
        except Exception as e:
            log(f"チェック中にエラー: {e}")

        # 60秒待機
        log(f"{LOOP_INTERVAL}秒後に再チェック")
        time.sleep(LOOP_INTERVAL)


if __name__ == "__main__":
    main()
