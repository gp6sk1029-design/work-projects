# 別PCでの再現手順（生産技術主任補佐PDM）

このリポジトリをGitHubから取得すれば、**ルール・手順・スクリプトは同じものが再現される**。
ただし**動かすには下記の環境が要る**（GitHubに入らないもの）。

## 1. GitHubから取得

```bash
git clone https://github.com/gp6sk1029-design/work-projects.git
cd work-projects
```

これで揃うもの：
- `CLAUDE.md` / `AGENTS.md`（全体ルール）※内容は同一。ツールによって読むファイルが違うだけ
- `MEMORY.md`（過去の学び・失敗パターン）
- `.claude/skills/`（Claude Code用スキル）／`.agents/skills/`（Codex等用・同じ内容）
- 各プロジェクトの `SKILL.md` とスクリプト

## 2. 必要なソフト（PCごとに個別インストール）

| ソフト | 用途 | 無いとどうなる |
|---|---|---|
| **Python 3.10以上** | スクリプト実行 | 何も動かない |
| **Microsoft Excel** | 注文書・会費表の読み書き（COM操作） | 注文書スキルが使えない |
| **SolidWorks** | 図面のDXF/PDF変換 | DXF変換スキルのみ使えない（他は動く） |
| **CubePDF** | 図面のPDF出力（印刷経由） | **PDFが作れない**。SolidWorks標準の書き出しは寸法線・枠が消えるため代用不可 |
| Git | 同期 | 手動コピーが必要 |

> CubePDFは https://www.cube-soft.jp/cubepdf/ から入手（無料）。
> インストール後、プリンタ一覧に「CubePDF」が出ていればOK。設定変更は不要
> （スクリプトが実行時だけ設定を借りて、終了時に元へ戻す）。

> Excel・SolidWorksは**Windows専用**。Mac/Linuxでは注文書入力とDXF変換は動かない
> （PDF読み取り・データ解析だけなら動く）。

## 3. Pythonパッケージ

```bash
pip install -r requirements.txt
```

## 4. アクセス権

- **NAS**（`\\nas-ime5\...`）に接続できること
  - 図面フォルダ：`\\nas-ime5\生産技術部\4.Drawing\...`
  - 会費テンプレ：`\\nas-ime5\現場_生産技術部\10.歓送迎会 会費\...`
- 社内ネットワークに接続していること

## 5. 動作確認

```bash
python tools/sync_skills.py --check     # スキルの同期状態
python -c "import openpyxl, fitz, win32com.client; print('OK')"
```

---

## PCごとに違って当たり前のもの（ハードコードしない）

| 項目 | 扱い |
|---|---|
| ユーザー名（`C:\Users\<名前>`） | スクリプトは `os.path.expanduser("~")` を使う。**絶対パスを埋め込まない** |
| デスクトップの作業ファイル | 各自のPCにあるもの。GitHubには**入れない**（個人情報・取引先情報のため） |
| 見積書PDF・図面・注文書Excel | **リポジトリに含めない**（.gitignoreで除外） |

## 秘匿情報の扱い（重要）

以下は**絶対にGitHubに置かない**：
- 取引先の見積単価・注文書の実データ
- 参加者名簿などの個人情報
- APIキー・パスワード

→ スキルの**手順とスクリプトだけ**を共有し、データは各PCのローカル／NASに置く。

---

## Codexなど他のAIツールで使う場合

- ルールは `AGENTS.md` を読む（`CLAUDE.md` と同じ内容）
- スキルは `.agents/skills/` にある。**自動で読み込まれない場合は、依頼時に
  「`.agents/skills/purchase-order/SKILL.md` を読んでから作業して」と伝える**
- スクリプトは素のPythonなので、どのツールからでも同じコマンドで実行できる
