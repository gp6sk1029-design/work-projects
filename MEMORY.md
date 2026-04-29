# 本業プロジェクト MEMORY.md
# 学習・経験の蓄積

> タスク完了のたびに追記する。効果がなかったパターンは削除する。月1回整理する。

---

## ツール開発のノウハウ

> **重要**: 以下のノウハウのうち「全ツール/アプリに適用すべき」レベルの汎用ルールは
> **CLAUDE.md の「ツール・アプリ開発の標準パターン」** に昇格済み。
> このMEMORY.mdには「昇格未満・プロジェクト横断の知見」を置く。
>
> エスカレーションの流れ：プロジェクト/MEMORY.md → work-projects/MEMORY.md → CLAUDE.md

### 共通パターン（全ツールに適用できる知見）

- **Webアプリ構成の鉄板**: client(React+Vite+Tailwind) + server(Express) が最速。SQLiteは必要になってから追加
- **Python+Express ブリッジ**: 既存Python CLIに `--json` オプションを追加すれば、Python側をほぼ書き換えずWeb化可能（drawing-checkerで実証）
- **ログとデータの分離**: Python側のログは必ず `sys.stderr` へ、JSONやデータは `sys.stdout.buffer.write(...encode('utf-8'))` へ。混在するとExpress側でJSONパース失敗
- **multer日本語ファイル名**: `Buffer.from(file.originalname, 'latin1').toString('utf-8')` でデコード必須
- **起動の自動化**: start.bat でバックエンド起動確認後にブラウザ自動起動。plc-debugger/drawing-checkerで実証
- **AI API選定**: テキスト処理はGemini 2.5 Flash（安い・速い）、高度な分析はClaude Sonnet
- **AIはオプトイン**: `--ai` フラグで明示的に有効化する形に。デフォルトOFFでAPIコスト抑制
- **JSONパースフォールバック**: AIは不正JSONを返すことがある → try/except で部分動作継続
- **日本語パス問題**: Windowsで日本語パスを含むスクリプトは英語パス経由のランチャーで回避
- **大容量ファイル**: dist/、node_modules/、.db、動画ファイル、uploads/ は.gitignoreで必ず除外
- **ファビコン必須**: ブラウザツールは必ず `client/public/favicon.svg` を設置（drawing-checkerで反省）
- **タイムスタンプ+ハッシュでファイル一意化**: アップロードファイルの同名上書きを防ぐ
- **機密データの除外**: 顧客図面・PII・学習結果は.gitignoreで必ず除外

### UI/フロントエンド
- 使用技術：React + TypeScript + Tailwind + Vite（固定）
- ダークモード前提（`<html class="dark">` ＋ Tailwind `darkMode:'class'`）
- タブUIでマルチ機能を1画面に統合するパターンが好評（メール秘書で実証）
- ファイルアップロード → 処理状況表示 → 結果表示の3ステップUIが直感的
- プレビュー＋結果パネルの左右2ペイン構成が情報密度と使いやすさのバランス最良（drawing-checkerで実証）
- 指摘/ログ/リストはクリックで該当箇所にジャンプする双方向ハイライトを実装すると体感が一段上がる

### バックエンド
- 使用技術：Node.js + Express（SQLiteは必要時のみ追加）
- SQLiteは単一ファイルDBなのでデプロイが楽。ただし.gitignoreで除外すること
- エクスポート・インポート機能を付けておくとデータ移行が楽（media-transcriberで実装済み）
- Python subprocess からのデータ取得は `spawn` + `PYTHONIOENCODING=utf-8` が定石
- ファイル配信は `Content-Type` と `Content-Disposition: inline` でブラウザ内プレビュー可能に

### Python スクリプト
- バックグラウンドデーモン: 無限ループ + sleep で定期実行（auto_draft.py方式）
- Windows Job Objectで孤児プロセス問題を解決（メール秘書で学んだ重要な知見）
- openpyxlのセル高さ自動計算: テキスト量に応じてcalc_h()関数で動的調整
- CLI設計: argparse の `nargs="+"` で複数ファイル/ディレクトリ受付可能に
- `--json` `--no-pdf` `--output-dir` などWeb連携用オプションを初期から組み込んでおく

### 管理機能（あると便利な共通機能）
- **学習/蓄積データの一覧・削除・再学習**：データ駆動ツールは「どのデータで学習したか」が見えると信頼性UP（drawing-checkerのサンプル管理機能で実証）
- **プレビュー機能**：一覧から1クリックで元データが見られるとデバッグ・確認が楽
- **リセット機能**：全データ削除のボタンを用意（ダイアログ付き）

---

## プロジェクト別の振り返り

### email-assistant（メール秘書）
- 開発期間: 2026/03/30 〜 2026/04/06（約1週間）
- 技術: Python + Gemini 2.5 Flash API + Thunderbird POP3/IMAP
- 主要な進化の流れ:
  1. 手動返信生成（対話型）→ 2. 自動下書き生成（バックグラウンド）→ 3. GUI統合（タブUI）→ 4. 文体自動学習 → 5. 手動下書き機能追加
- **学び**:
  - Thunderbird再起動は全件処理後に1回だけが正解（毎件やるとPC負担大）
  - チェック間隔は30分が適切（1分は過剰、60分は遅い）
  - 件名行を返信文に含めないよう注意（最初のバグ）
  - 文体設定（style_profile.json）で自然な返信文が生成できる
  - VBSランチャー経由で日本語パス問題を回避
  - 生産技術部フォルダは末尾読みで対象に追加（フォルダ構造の癖）
  - 手動下書きでメール一覧がThunderbirdと異なる問題 → ソート順の違いが原因
  - 多重実行バグ → ロック機構で解決

### plc-debugger（PLCデバッガ / PLC Craft AI）
- 開発期間: 2026/04/07 〜 2026/04/08（2日間）
- 技術: React + TypeScript + Tailwind + Vite（client）/ Node.js + Express + SQLite（server）
- Gemini AI連携 + IEC 61131-3準拠
- 主要機能: .smc2ファイル解析、PLCプログラム分析、フローチャート生成、トラブルシュート、HMI分析、総合診断
- **学び**:
  - Sysmac Studio .smc2ファイルはXML形式 → パーサーで構造解析可能
  - 大規模機能強化を2日で実現（Gemini AI連携・IEC準拠・フローチャート刷新）
  - 使い方ガイドをアプリ内に組み込むとユーザー体験が向上
  - セキュリティ修正: .envファイルのAPIキー管理を徹底
  - PC起動時の自動起動はWindowsタスクスケジューラで設定

### media-transcriber（文字起こしツール）
- 開発期間: 2026/04/10 〜 2026/04/13（4日間）
- 技術: React + TypeScript + Tailwind + Vite（client）/ Node.js + Express + SQLite（server）
- Gemini API連携 + FFmpeg音声処理
- 主要機能: 動画/音声アップロード → AI文字起こし → 要約 → セクション分割 → Q&Aチャット → マインドマップ → エクスポート/インポート
- **学び**:
  - 雑音除去をFFmpegで前処理すると文字起こし精度が大幅に向上
  - JSONパース強化: AIの応答が不正なJSONを返す場合がある → フォールバック処理必須
  - 履歴削除はファイル+DB同時削除が必要（片方だけだと不整合）
  - エクスポート/インポート機能はデータ移行・バックアップに必須
  - 大容量の動画ファイルはgitに入れないこと（.gitignoreで除外）

### winding-report（巻線レポート）
- 技術: Python + openpyxl
- Excel自動生成で改善報告書を作成
- **学び**:
  - openpyxlの行高さ自動計算: テキスト量とセル幅から動的に算出するcalc_h()関数が必須
  - 画像挿入とテーブル構造の組み合わせは配置調整が難しい

#### 2026-04-17 AISIN軌跡計算ファイルへSLM8000方式の移植（append_slm8000_method.py）
- 対象: `2976 LXLZ軌跡計算式_20230525.xlsx`（AISIN）＋`【巻線検証】SLM8000軌道_H2X ZS L 400rpm.xls` のロジック
- 手法: openpyxl で既存ファイルに新規シート「SLM8000方式_軌道計算」を1枚追加、ScatterChart 2枚（指令位置軌道・実測位置軌道）
- 合意事項（ユーザー回答）:
  - 2パターン = AISIN方式 と SLM8000方式 の計算ロジック2種類
  - ワーク寸法 = L1・R の幾何寸法 ＋ 製品図形の座標 両方
  - データ入力 = コピペ方式（CSV → セル貼り付け）
  - 軸マッピング: θ → LX（水平・振り軸）、Z → LZ（送り軸）
- **学び**:
  - NAS UNCパスは WSL/Bash セッションから直接読めないことがある → ローカル(/tmp または AppData\Local\Temp)にコピーして作業
  - Python(Win) の `/tmp` は Bash(MSYS) の /tmp と別物。スクリプトでは `%TEMP%\winding_analysis\` など絶対パスで指定
  - 旧xls形式は `xlrd 2.0.1` で読める（`open_workbook(path, formatting_info=False)`）が、数式本体は取得不可で計算値のみ取れる
  - openpyxl で既存xlsxに新規シートを追加する際は `load_workbook` → `create_sheet` → `save`。既存ChartObjectsは保持されるが「Data Validation extension is not supported」警告が出る（無害）
  - xlsxの既存ScatterChartはすべて保持できた（8シート × 各1チャート = 8個、保存後も 1→1 変化なし）
  - ユーザーがExcelで該当ファイルを開いていると `~$` ロックファイルが出る。編集時はファイル別名コピー（`_NEW.xlsx`）で回避し、最後にユーザーにリネーム依頼
  - 新規シートで参照元に `='等加速度20230825'!F6` のように日本語シート名参照可能（シート名を `'` で囲む）
  - ScatterChart の Series は `Series(y_ref, x_ref, title=...)` の順（y, x の順番に注意）
  - グラフ2枚を同じシートに配置する際、`ws.add_chart(chart, 'L16')` と `'L42'` のように上下に並べると視認性良好
  - 空入力対応: `=IF(C9="","",C9-LX!$C$4)` で空セルを透過させると、データ未入力時もグラフ崩れなし
- **ROI試算**: 月50分削減 × 時給3,000円 = 月2,500円 × 年30,000円相当 / 開発1.5h / 回収期間約2ヶ月
- **2回目改修での追加学び（2026-04-17 同日の追加リクエスト対応）**:
  - 初回の単純引き算式ではSysmac Studio角度(0-360°)をそのまま扱えなかった → AISIN既存の三角関数式 `R·cosθ + √(L1² − (R·sinθ)²) − L1` に置換して物理mm変位化
  - ScatterChartの既定scatterStyle=Noneだと「点のみ」表示で四角形の輪郭が繋がらない → `chart.scatterStyle = 'lineMarker'` で閉ループ描画
  - Chart軸スケールを `chart.x_axis.scaling.min/max` で ±20mm 固定しないと、軌道データの広いレンジに引っ張られて製品輪郭が潰れる
  - 系列ごとの色分けは `from openpyxl.drawing.line import LineProperties; series.graphicalProperties = GraphicalProperties(ln=LineProperties(w=19050, solidFill='4472C4', prstDash='solid'))`。線幅は EMU 単位（12700≈1pt, 19050≈1.5pt, 31750≈2.5pt）
  - マーカー色は `Marker(symbol='circle', size=4)` に `marker.graphicalProperties = GraphicalProperties(solidFill='4472C4')` 併設
  - 指令値(青 circle) / 実測値(橙 diamond) / 製品輪郭(濃緑 square 太線) の3系列色分けが比較に有効
  - 左右軸(S/U)対応は列を ABCDEFGHIJ (左) + L〜U (右) に分割、右側はLZを `=E列参照` で左に追従させると運用が楽
  - `chart.legend.position = 'b'` で凡例を下に配置するとグラフエリアが広く使える

### farewell-docs（送別会書類）
- 技術: Python + openpyxl / HTML
- Excel版とHTML版の両方を自動生成
- **学び**:
  - デスクトップパスに日本語が含まれる場合の対処が必要

### drawing-checker（SolidWorks 2D図面 検図ツール）
- 開発開始日: 2026-04-15
- 技術: Python 3.10+ / PyMuPDF / ezdxf / OpenCV+Tesseract / pywin32 (SolidWorks COM) / google-genai (Gemini 2.5 Flash) / tkinter + tkinterdnd2
- 対応形式: PDF, DXF, DWG（ODA File Converter経由）, SLDDRW, PNG/JPG
- 主要機能:
  1. 4系統の検図（寸法・タイトルブロック・線種/投影法・表面粗さ/幾何公差/溶接記号）
  2. 検図結果を赤ペン風にPDFへ直接マーキング＋HTMLサマリレポート
  3. サンプル図面から社内ルールを自動学習（config/learned_rules.json）
  4. 3層ルール合成（learned > JIS > fallback）
  5. AI補完レイヤー（--aiフラグ、Gemini 2.5 Flash）
  6. GUI/CLI/ドラッグ&ドロップ（.bat/.vbs）対応
- **ROI試算**: 手動検図20分/枚 → ツール8分/枚（年48h削減・約14万円相当） / 開発コスト約20h / 回収期間約5ヶ月
- **学び**（初版実装時）:
  - JIS規格をハードコード＋サンプル学習の3層構造でルール汎用化
  - JIS必須ルール（第三角法マーク・幾何公差3要素・普通公差明示）は`override_by_sample: false`で保護
  - PyMuPDFはY座標が上向き⇔下向きで注釈座標に注意（高さ-yで変換必要）
  - SolidWorks COM APIは環境依存が強い → グレースフルに失敗させる実装必須
  - ezdxfはDXF読み込み失敗時 `recover.readfile`でリトライできる
  - Geminiのルール学習／違和感検出は`--ai`オプトイン方式でAPIコスト抑制
  - ODA File ConverterはCLIで入出力ディレクトリ指定方式（ファイル直接指定不可）
  - 動作確認: 4チェッカーすべてダミー図面で例外なく実行・11件の指摘を正しく検出
  - CLAUDE.md準拠でSKILL.md冒頭にROI試算・自己改善ループ記載

---

## 失敗パターン（二度と繰り返さないこと）

| 日付 | 失敗 | 原因 | 対策 |
|---|---|---|---|
| 2026/04/02 | メール秘書がThunderbirdを毎件再起動してPC負荷大 | 再起動タイミングの設計ミス | 全件処理後に1回だけ再起動 |
| 2026/04/03 | 孤児プロセスが残り続ける | プロセス管理の欠如 | Windows Job Objectで親プロセスと連動 |
| 2026/04/03 | 返信文に件名行が含まれてしまう | プロンプト設計の不備 | 出力フォーマットを明示的に指定 |
| 2026/04/06 | 手動下書きの多重実行 | ボタン連打対策なし | ロック機構（実行中フラグ）を追加 |
| 2026/04/06 | メール一覧がThunderbirdと異なる | ソート順の違い | Thunderbirdと同じソート順に統一 |
| 2026/04/13 | 文字起こしのJSONパースエラー | AIが不正なJSON返却 | フォールバック処理を追加 |
| 2026/04/14 | 動画ファイルがgitに入ってpush失敗 | .gitignore漏れ | uploads/を.gitignoreに追加 |
| 2026/04/15 | drawing-checkerブラウザ版でfavicon未設置のまま完成させた | Viteテンプレの既定faviconが無いことに気づかなかった | **今後、ブラウザツールは初期構築時にfavicon.svg設置を必須化**（CLAUDE.mdに明文化） |

---

## インフラ・運用のノウハウ

### GitHub同期（2台PC間）
- SessionStartフックで自動pull、Stopフックで自動commit&push
- push失敗時は.claude/.push_failedに記録、次回起動時に警告
- 本業（work-projects）と副業（my-ai-company）はリポジトリを分離

### MacBookセットアップ
- `bash <(curl -s https://raw.githubusercontent.com/.../setup_mac.sh)` で1行クローン
- .claude/settings.jsonがcloneに含まれるので追加設定不要

### Windows固有の注意点
- 日本語パスは英語パスランチャー経由で回避
- CRLFとLFの混在警告は無害（git config autocrlf=trueで対応可能）

---

## 更新履歴

| 日付 | 更新者 | 内容 |
|---|---|---|
| 2026-04-14 | 初期作成 | テンプレート作成 |
| 2026-04-14 | Claude | 2026/03/30〜04/14の全開発履歴を遡及記録 |
| 2026-04-15 | Claude | drawing-checker（図面検図ツール）プロジェクト初版実装・振り返り記録 |
| 2026-04-17 | Claude | winding-report: AISIN軌跡計算Excelに SLM8000方式シート追加（append_slm8000_method.py）・ノウハウ追記 |
