# -*- coding: utf-8 -*-
"""SolidWorks図面(.SLDDRW)をDXFへ一括変換する（起動済みSolidWorksに接続）。

原本は読み取り専用で開き、変更しない。1件ずつログに残し、失敗しても継続する。

使い方:
    python batch_dxf.py --src "<図面フォルダ>" --check          # 件数と接続確認のみ
    python batch_dxf.py --src "<図面フォルダ>" --out "<出力先>"  # 変換実行
    python batch_dxf.py --src "..." --out "..." --skip-existing  # 既存DXFはスキップ

※ SolidWorksは事前に手動で起動しておくこと（自動起動すると落ちる）
"""
import sys, os, time, json, argparse, traceback

sys.stdout.reconfigure(encoding="utf-8")
import win32com.client
import pythoncom

swDocDRAWING = 3
swOpenDocOptions_ReadOnly = 2


def fix_path(p):
    r"""シェル経由でバックスラッシュが潰れたUNCパスを復元する。

    bashは "\\nas\share" を "\nas\share" にしてしまうことがある。
    また "//nas/share" 形式で渡ってくる場合もあるため両方を吸収する。
    """
    if not p:
        return p
    p = p.replace("/", "\\") if p.startswith("//") else p
    if p.startswith("\\") and not p.startswith("\\\\"):
        p = "\\" + p                      # \nas-ime5\... → \\nas-ime5\...
    return p
ERRMAP = {1: "汎用エラー", 2: "ファイルなし", 4: "不正な形式", 8: "読取専用不可",
          16: "使用中", 32: "参照ファイル不足", 64: "要リビルド", 128: "アクセス拒否",
          256: "低バージョン", 512: "変換不可", 1024: "未来バージョン(このSWより新しい)",
          2048: "パスワード保護"}


def connect():
    """起動済みSolidWorksに接続する。起動していなければNone"""
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
        rev = sw.RevisionNumber
        return sw, (rev() if callable(rev) else rev)
    except Exception:
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="図面フォルダ（NASのUNCパス可）")
    ap.add_argument("--out", default=r"C:\Users\SEIGI-N13\Desktop\DXF変換")
    ap.add_argument("--check", action="store_true", help="件数と接続確認のみ")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()
    a.src, a.out = fix_path(a.src), fix_path(a.out)

    if not os.path.isdir(a.src):
        print("NG: フォルダにアクセスできません:", a.src)
        print("   ヒント: UNCパスはシェルでバックスラッシュが失われることがあります。")
        print("   その場合は --src を \"//nas-ime5/共有名/...\" 形式で渡してください。")
        return 1
    files = sorted(f for f in os.listdir(a.src) if f.lower().endswith(".slddrw"))
    print("図面フォルダ:", a.src)
    print(f"  SLDDRW: {len(files)} 件")

    sw, rev = connect()
    if sw is None:
        print("\n❌ SolidWorksに接続できません。")
        print("   → SolidWorksを手動で起動してから、もう一度実行してください。")
        print("   （自動起動させると初期化中に落ちるため、手動起動が必要です）")
        return 1
    print(f"  SolidWorks: 接続OK（バージョン {rev}）")

    if a.check:
        print("\n--check のため変換は行いません。")
        return 0

    os.makedirs(a.out, exist_ok=True)
    log_path = os.path.join(os.environ.get("TEMP", "."), "dxf_batch_log.txt")
    open(log_path, "w", encoding="utf-8").close()

    def log(m):
        print(m, flush=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(m + "\n")

    log(f"変換開始: {len(files)}件 → {a.out}")
    sw.Visible = True
    results, t_all = [], time.time()
    for i, fn in enumerate(files, 1):
        src = os.path.join(a.src, fn)
        dst = os.path.join(a.out, os.path.splitext(fn)[0] + ".dxf")
        rec = {"no": i, "file": fn, "ok": False, "err": "", "size": 0, "sec": 0}
        if a.skip_existing and os.path.exists(dst):
            rec.update(ok=True, size=os.path.getsize(dst), err="既存のためスキップ")
            results.append(rec)
            log(f"[{i:3d}/{len(files)}] -- {fn}  （既存スキップ）")
            continue
        t0 = time.time()
        try:
            errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            doc = sw.OpenDoc6(src, swDocDRAWING, swOpenDocOptions_ReadOnly, "", errors, warnings)
            if doc is None:
                e = errors.value
                detail = "/".join(v for k, v in ERRMAP.items() if e & k) or f"code={e}"
                rec["err"] = "開けない: " + detail
            else:
                title = doc.GetTitle
                title = title() if callable(title) else title
                doc.SaveAs3(dst, 0, 0)
                time.sleep(0.4)
                try:
                    sw.CloseDoc(title)
                except Exception:
                    pass
                if os.path.exists(dst):
                    rec["ok"] = True
                    rec["size"] = os.path.getsize(dst)
                else:
                    rec["err"] = "DXFが出力されなかった"
        except pythoncom.com_error as ce:
            rec["err"] = f"COMエラー: {ce.args[1] if len(ce.args) > 1 else ce}"
        except Exception as ex:
            rec["err"] = f"例外: {ex}"
        rec["sec"] = round(time.time() - t0, 1)
        results.append(rec)
        log(f"[{i:3d}/{len(files)}] {'OK ' if rec['ok'] else 'NG '} {fn}  "
            f"{rec['size']:,}B  {rec['sec']}s  {rec['err']}")
        json.dump(results, open(os.path.join(os.environ.get("TEMP", "."),
                                             "dxf_batch_result.json"), "w",
                                encoding="utf-8"), ensure_ascii=False)

    ok = sum(1 for r in results if r["ok"])
    log(f"\n=== 完了 {ok}/{len(files)} 件成功  所要 {time.time()-t_all:.0f}秒 ===")
    ng = [r for r in results if not r["ok"]]
    if ng:
        log("失敗した図面:")
        for r in ng:
            log(f"  {r['file']}: {r['err']}")
    log("※ SolidWorksは起動したままです（図面のみ閉じました）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("致命的エラー:\n" + traceback.format_exc())
        sys.exit(1)
