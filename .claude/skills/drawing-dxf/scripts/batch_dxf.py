# -*- coding: utf-8 -*-
"""SolidWorks図面(.SLDDRW)をDXF/PDFへ一括変換する（起動済みSolidWorksに接続）。

原本は読み取り専用で開き、変更しない。1件ずつログに残し、失敗しても継続する。

PDFは **CubePDFへ印刷** して作る（既定）。
SolidWorks標準の SaveAs3 によるPDF書き出しは、寸法線・矢印・図面枠・表題欄の罫線が
欠落して文字だけになる不具合があるため使わない（2026-08-12 実機で確認）。

使い方:
    python batch_dxf.py --src "<図面フォルダ>" --check          # 件数と接続確認のみ
    python batch_dxf.py --src "<図面フォルダ>" --out "<出力先>"  # 変換実行（DXFのみ）
    python batch_dxf.py --src "..." --out "..." --format dxf,pdf # DXFとPDF
    python batch_dxf.py --src "..." --out "..." --skip-existing  # 既存分はスキップ

※ SolidWorksは事前に手動で起動しておくこと（自動起動すると落ちる）
※ PDFにはCubePDFのインストールが必要（C:\\Program Files\\CubePDF）
"""
import sys, os, time, json, argparse, traceback, subprocess, winreg, tempfile, shutil

sys.stdout.reconfigure(encoding="utf-8")
import win32com.client
import pythoncom

swDocDRAWING = 3
swOpenDocOptions_ReadOnly = 2
swPageSetupInUse_Document = 2
swPageSetupOrient_Portrait, swPageSetupOrient_Landscape = 1, 2

CUBEPDF_EXE = r"C:\Program Files\CubePDF\CubePdf.exe"
CUBEPDF_KEY = r"Software\CubeSoft\CubePDF\v2"

# 用紙コード＝Windows標準のDMPAPER値（実測で確定：A5=11 / A4=9 / A3=8 / A2=66）。
# カスタム用紙(256)はCubePDFドライバが非対応でA4に落ちるため使わない。
PAPERS = [(148, 210, 11, "A5"), (210, 297, 9, "A4"),
          (297, 420, 8, "A3"), (420, 594, 66, "A2")]


def paper_for(wmm, hmm):
    """シート寸法(mm)から (用紙コード, 向き, 用紙名, 収まらない場合の警告) を返す"""
    short, long_ = sorted((wmm, hmm))
    orient = (swPageSetupOrient_Landscape if wmm >= hmm
              else swPageSetupOrient_Portrait)
    for ps, pl, code, name in PAPERS:
        if short <= ps + 2 and long_ <= pl + 2:
            return code, orient, name, ""
    # A1/A0はWindowsの用紙規格に無い → A2へ縮小（内容は欠けない）
    return 66, orient, "A2", f"{short}x{long_}mmはA2用紙へ縮小出力"



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


class CubePdf:
    """CubePDFをダイアログなし(-SkipUI)で動かす。

    保存先は「レジストリ LastAccess のフォルダ ＋ -DocumentName ＋ .pdf」で決まる仕様。
    -Destination 引数は無視されるため、LastAccess を毎回書き換えて制御する。
    ユーザーの設定は開始時に退避し、終了時に必ず元へ戻す。
    """

    # 一時的に強制する設定（値はこの環境で実測確認済み）
    FORCE = {"FileType": 3,        # PDF
             "PostProcess": 0,     # 変換後に何もしない（ビューアを開かせない）
             "ExistedFile": 0}     # 同名ファイルは上書き

    def __init__(self, exe=CUBEPDF_EXE, timeout=300):
        self.exe, self.timeout, self.saved, self.key = exe, timeout, {}, None

    def available(self):
        return os.path.exists(self.exe)

    def open(self):
        """設定を退避してから、バッチ用の設定を書き込む"""
        self.key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, CUBEPDF_KEY, 0,
                                  winreg.KEY_READ | winreg.KEY_WRITE)
        for name in list(self.FORCE) + ["LastAccess"]:
            try:
                self.saved[name] = winreg.QueryValueEx(self.key, name)
            except FileNotFoundError:
                pass
        for name, val in self.FORCE.items():
            winreg.SetValueEx(self.key, name, 0, winreg.REG_DWORD, val)
        return self

    def close(self):
        """退避しておいたユーザー設定へ戻す（失敗しても止めない）"""
        for name, (val, typ) in self.saved.items():
            try:
                winreg.SetValueEx(self.key, name, 0, typ, val)
            except Exception:
                pass
        if self.key:
            self.key.Close()
            self.key = None

    def convert(self, ps_path, dst_pdf):
        """PSファイルをPDFへ変換する。成功したらTrue"""
        base = os.path.splitext(os.path.basename(dst_pdf))[0]
        winreg.SetValueEx(self.key, "LastAccess", 0, winreg.REG_SZ, dst_pdf)
        if os.path.exists(dst_pdf):
            os.remove(dst_pdf)          # 上書き時の "(2)" 生成を確実に防ぐ
        subprocess.run([self.exe, "-DocumentName", base,
                        "-InputFile", ps_path, "-SkipUI", "true"],
                       timeout=self.timeout, capture_output=True)
        for _ in range(20):             # 保存完了まで少し待つ
            if os.path.exists(dst_pdf) and os.path.getsize(dst_pdf) > 0:
                return True
            time.sleep(0.3)
        return False


def sheet_sizes(doc):
    """各シートの寸法(mm)を [(シート名, 幅, 高さ), ...] で返す"""
    names = doc.GetSheetNames
    if isinstance(names, str):
        names = [names]
    out = []
    for nm in names:
        w = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8, 0.0)
        h = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8, 0.0)
        try:
            sh = doc.Sheet(nm)
            sh.GetSize(w, h)
        except Exception:               # 取得できないときは表示して測る
            doc.ActivateSheet(nm)
            doc.GetCurrentSheet.GetSize(w, h)
        out.append((nm, round(w.value * 1000), round(h.value * 1000)))
    return out


def export_pdf_via_cubepdf(doc, dst_pdf, cube, printer, scale_to_fit, tmpdir, note):
    """図面をCubePDFへ印刷してPDF化する。複数シートは1つのPDFに結合する。

    戻り値: 生成できたらTrue
    """
    sheets = sheet_sizes(doc)
    doc.Extension.UsePageSetup = swPageSetupInUse_Document
    parts = []
    for i, (nm, wmm, hmm) in enumerate(sheets, 1):
        code, orient, pname, warn = paper_for(wmm, hmm)
        if warn:
            note.append(f"シート{i}: {warn}")
        st = doc.PageSetup
        st.PrinterPaperSize = code
        st.Orientation = orient
        st.ScaleToFit = bool(scale_to_fit)
        if not scale_to_fit:
            st.Scale2 = 100.0
        st.HighQuality = True

        ps_path = os.path.join(tmpdir, f"sheet{i}.ps")
        if os.path.exists(ps_path):
            os.remove(ps_path)
        pages = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I4, [i])
        doc.Extension.PrintOut3(pages, 1, False, printer, ps_path, True)
        for _ in range(60):
            if os.path.exists(ps_path) and os.path.getsize(ps_path) > 0:
                break
            time.sleep(0.5)
        if not os.path.exists(ps_path):
            note.append(f"シート{i}: 印刷ファイルが作られませんでした")
            return False

        part = dst_pdf if len(sheets) == 1 else os.path.join(tmpdir, f"part{i}.pdf")
        ok = cube.convert(ps_path, part)
        os.remove(ps_path)
        if not ok:
            note.append(f"シート{i}: CubePDFが出力しませんでした")
            return False
        parts.append(part)

    if len(parts) > 1:                  # 複数シートを1ファイルへ結合
        import fitz
        merged = fitz.open()
        for p in parts:
            with fitz.open(p) as d:
                merged.insert_pdf(d)
        merged.save(dst_pdf)
        merged.close()
        for p in parts:
            os.remove(p)
    return os.path.exists(dst_pdf)


def produced_ok(dst, t_start):
    """本当に今回作られたファイルかを確かめる。

    ビューアで開いたままのファイルは削除も上書きもできず、**古いファイルが残る**。
    存在チェックだけだと成功と誤判定するため、更新時刻と中身も見る。
    戻り値: (成功か, 失敗理由)
    """
    if not os.path.exists(dst):
        return False, "出力されませんでした"
    if os.path.getsize(dst) == 0:
        return False, "中身が空です"
    if os.path.getmtime(dst) < t_start - 2:
        return False, "古いファイルが残っています（ビューア等で開いていないか確認）"
    if dst.lower().endswith(".pdf"):
        try:
            with open(dst, "rb") as f:
                if f.read(5) != b"%PDF-":
                    return False, "PDFとして壊れています"
        except OSError as e:
            return False, f"読めません（使用中の可能性）: {e.strerror}"
    return True, ""


def convert_one(sw, src, dsts, cube, a, tmpdir):
    """図面1件を開いて、指定形式すべてを書き出す。原本は読み取り専用で変更しない。"""
    rec = {"ok": False, "err": "", "size": 0, "made": [], "note": []}
    doc = None
    title = None
    try:
        errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        doc = sw.OpenDoc6(src, swDocDRAWING, swOpenDocOptions_ReadOnly, "",
                          errors, warnings)
        if doc is None:
            e = errors.value
            detail = "/".join(v for k, v in ERRMAP.items() if e & k) or f"code={e}"
            rec["err"] = "開けない: " + detail
            return rec

        title = doc.GetTitle
        title = title() if callable(title) else title
        miss = []
        for fmt, dst in dsts.items():        # 1回開いて全形式を書き出す
            t_start = time.time()
            if os.path.exists(dst):
                try:
                    os.remove(dst)           # 上書き前に消す（残骸との取り違え防止）
                except OSError:
                    pass                     # 消せなくても続行し、後の判定でNGにする
            if fmt == "pdf" and cube is not None:
                export_pdf_via_cubepdf(doc, dst, cube, a.printer,
                                       a.pdf_scale == "fit", tmpdir, rec["note"])
            else:
                doc.SaveAs3(dst, 0, 0)
                time.sleep(0.4)
            ok, why = produced_ok(dst, t_start)
            if ok:
                rec["made"].append(fmt)
                rec["size"] += os.path.getsize(dst)
            else:
                miss.append(f"{fmt}（{why}）")
        if miss:
            rec["err"] = "出力できず: " + " / ".join(miss)
        rec["ok"] = not miss
    except pythoncom.com_error as ce:
        rec["err"] = f"COMエラー: {ce.args[1] if len(ce.args) > 1 else ce}"
    except Exception as ex:
        rec["err"] = f"例外: {ex}"
    finally:
        if title:
            try:
                sw.CloseDoc(title)
            except Exception:
                pass
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="図面フォルダ（NASのUNCパス可）")
    ap.add_argument("--out",
                    default=os.path.join(os.path.expanduser("~"), "Desktop", "DXF変換"),
                    help="出力先（既定：デスクトップのDXF変換フォルダ）")
    ap.add_argument("--check", action="store_true", help="件数と接続確認のみ")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="先頭N件だけ処理する（本番前の試し出力用）")
    ap.add_argument("--only", default="",
                    help="ファイル名にこの文字を含む図面だけ処理する（1件だけ作り直す用）")
    ap.add_argument("--format", default="dxf",
                    help="出力形式をカンマ区切りで指定（dxf / pdf / dxf,pdf）")
    ap.add_argument("--pdf-engine", default="cubepdf", choices=["cubepdf", "solidworks"],
                    help="PDFの作り方（既定cubepdf＝印刷経由。solidworksは線が抜けるため非推奨）")
    ap.add_argument("--printer", default="CubePDF", help="印刷に使うプリンタ名")
    ap.add_argument("--pdf-scale", default="fit", choices=["fit", "actual"],
                    help="fit=用紙に合わせる（既定・欠けない） / actual=100%%のまま")
    a = ap.parse_args()
    formats = [f.strip().lower() for f in a.format.split(",") if f.strip()]
    for f in formats:
        if f not in ("dxf", "pdf"):
            print(f"NG: 未対応の形式です: {f}（dxf / pdf のみ）")
            return 1
    a.src, a.out = fix_path(a.src), fix_path(a.out)

    if not os.path.isdir(a.src):
        print("NG: フォルダにアクセスできません:", a.src)
        print("   ヒント: UNCパスはシェルでバックスラッシュが失われることがあります。")
        print("   その場合は --src を \"//nas-ime5/共有名/...\" 形式で渡してください。")
        return 1
    files = sorted(f for f in os.listdir(a.src) if f.lower().endswith(".slddrw"))
    print("図面フォルダ:", a.src)
    print(f"  SLDDRW: {len(files)} 件")
    if a.only:
        files = [f for f in files if a.only in f]
        print(f"  → --only「{a.only}」に一致する {len(files)} 件のみ処理します")
        if not files:
            print("NG: 一致する図面がありません。")
            return 1
    if a.limit > 0:
        files = files[:a.limit]
        print(f"  → --limit により先頭 {len(files)} 件のみ処理します")

    sw, rev = connect()
    if sw is None:
        print("\n❌ SolidWorksに接続できません。")
        print("   → SolidWorksを手動で起動してから、もう一度実行してください。")
        print("   （自動起動させると初期化中に落ちるため、手動起動が必要です）")
        return 1
    print(f"  SolidWorks: 接続OK（バージョン {rev}）")

    # PDFをCubePDF経由で作る場合の事前チェック
    cube = None
    if "pdf" in formats and a.pdf_engine == "cubepdf":
        cube = CubePdf()
        if not cube.available():
            print("\n❌ CubePDFが見つかりません:", CUBEPDF_EXE)
            print("   → CubePDFをインストールするか、--pdf-engine solidworks を指定してください")
            print("     （ただしsolidworks指定は寸法線などが欠落するため非推奨）")
            return 1
        try:
            import win32print
            names = [p[2] for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            if a.printer not in names:
                print(f"\n❌ プリンタ「{a.printer}」が見つかりません。")
                print("   利用可能:", " / ".join(names))
                return 1
        except ImportError:
            pass
        print(f"  PDF出力: CubePDF経由（プリンタ「{a.printer}」・"
              f"{'用紙に合わせる' if a.pdf_scale == 'fit' else '100%'}）")
    elif "pdf" in formats:
        print("  ⚠️ PDF出力: SolidWorks標準（寸法線・枠が欠落する既知の不具合あり）")

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

    log(f"変換開始: {len(files)}件 → {a.out}  形式: {'/'.join(formats)}"
        + (f"  PDF={a.pdf_engine}" if "pdf" in formats else ""))
    sw.Visible = True
    if cube:
        cube.open()
    tmpdir = tempfile.mkdtemp(prefix="swpdf_")
    results, t_all = [], time.time()
    try:
        for i, fn in enumerate(files, 1):
            src = os.path.join(a.src, fn)
            base = os.path.splitext(fn)[0]
            dsts = {f: os.path.join(a.out, base + "." + f) for f in formats}
            if a.skip_existing and all(os.path.exists(p) for p in dsts.values()):
                rec = {"no": i, "file": fn, "ok": True, "err": "既存のためスキップ",
                       "size": sum(os.path.getsize(p) for p in dsts.values()),
                       "sec": 0, "made": list(dsts), "note": []}
                results.append(rec)
                log(f"[{i:3d}/{len(files)}] -- {fn}  （既存スキップ）")
                continue

            t0 = time.time()
            rec = convert_one(sw, src, dsts, cube, a, tmpdir)
            rec.update(no=i, file=fn, sec=round(time.time() - t0, 1))
            results.append(rec)
            log(f"[{i:3d}/{len(files)}] {'OK ' if rec['ok'] else 'NG '} {fn}  "
                f"[{'+'.join(rec['made']) or '-'}]  {rec['size']:,}B  {rec['sec']}s  "
                f"{rec['err']}{'  ※' + ' / '.join(rec['note']) if rec['note'] else ''}")
            json.dump(results, open(os.path.join(os.environ.get("TEMP", "."),
                                                 "dxf_batch_result.json"), "w",
                                    encoding="utf-8"), ensure_ascii=False)
    finally:
        if cube:
            cube.close()                 # ユーザーのCubePDF設定を必ず戻す
        shutil.rmtree(tmpdir, ignore_errors=True)

    ok = sum(1 for r in results if r["ok"])
    log(f"\n=== 完了 {ok}/{len(files)} 件成功  所要 {time.time()-t_all:.0f}秒 ===")
    ng = [r for r in results if not r["ok"]]
    if ng:
        log("失敗した図面:")
        for r in ng:
            log(f"  {r['file']}: {r['err']}")
    notes = [(r["file"], n) for r in results for n in r.get("note", [])]
    if notes:
        log("注意した図面:")
        for f, n in notes:
            log(f"  {f}: {n}")
    log("※ SolidWorksは起動したままです（図面のみ閉じました）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("致命的エラー:\n" + traceback.format_exc())
        sys.exit(1)
