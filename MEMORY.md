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

### 会費収支管理テンプレート（歓送迎会・farewell-docs関連）
- 場所: `\\nas-ime5\現場_生産技術部\10.歓送迎会 会費\`（NAS上で運用。gitには入れない＝機密分離）
- 2026-07-14 改修: ①役職別会費・ご支援金 ②最大40名化 ③状況欄（アルコール/食事制限/送迎のドロップダウン＋自動集計）④開催店舗/住所/URL欄 ⑤固定費に送迎バス代
- 2026-07-14 追加改修（_20260714C）: 役職に「技師」「主任」を追加（社員と係長の間）。最新版は **_20260714C（11役職）**
  - **役職を2グループで管理**: 一律返金グループ（社員・技師・主任＝設定シートB14:B16・ご支援金0）と役職者グループ（係長〜社長＝B17:B24・ご支援金あり・按分返金）
  - グループ人数カウントは `SUMPRODUCT(COUNTIF(D7:D46,設定!$B$14:$B$16))`（一般）/ `SUMPRODUCT(COUNTIF(D7:D46,設定!$B$17:$B$24))`（役職者）。役職を増減するときは①設定シートの役職テーブル行、②この2つのカウント範囲、③会費/支援金のINDEX/MATCH範囲、④注記・返金設定の行番号、の4点を必ず同時に更新
  - 生成スクリプト: scratchの `rebuild_v3.py`。役職リストは `RANKS` と `FLAT_GROUP`（一律返金グループ）の2定数で制御
  - 2026-07-14 さらに変更: 係長も一般（一律返金）グループへ移動。現在 `FLAT_GROUP=[社員,技師,主任,係長]`（B14:B17）、役職者＝課長以上（B18:B24）。**グループ境界を動かすときはFLAT_GROUPとCNT_SHAIN/CNT_YAKUのセル範囲を必ずセットで直す**
  - **⚠️やらかし**: テンプレート再生成時、`set_date_com.py`（Excel COMでの日付書式焼き込み＆再計算）を本体に流し忘れて納品→openpyxl保存のまま（サイズが小さいのが兆候）で日付書式がExcelで化ける状態だった。**再生成フローは必ず rebuild→make_test→set_date_com（本体にも）→検証→納品 の順を守る**
  - 2026-07-14 追加: 固定費・変動費の各項目＋合計に「1人当たり」列（I列）を追加。頭割りの分母 `PAX=(CNT_SHAIN+CNT_YAKU)`＝会費負担者（招待・欠席を除く実参加者）。式は `=IF(OR(F{r}="",{PAX}=0),"",ROUND(F{r}/{PAX},0))`。I列幅は11→13に拡張（参加者テーブルの食事制限列と共用）
  - 2026-07-14 追加: 一般返金額を「設定額が上限・余剰金が足りなければ自動減額」に改善。`F101=IF(OR(F98<=0,一般人数=0),0,MIN(設定額,ROUNDDOWN(余剰金/一般人数,0)))`。減額時は説明セルに「※余剰金が不足のため設定額○円から自動減額」と理由を自動表示。**旧版の穴（固定額返金が余剰金を超えて赤字化）を解消**。不足/潤沢の両ケースでテスト検証済み
  - 2026-07-14 追加: 固定費・変動費を「1人当たり予算」入力→予算合計自動算出方式に再構成。列を1つ拡張し **E=1人当たり予算(入力) / F=予算合計(=E×人数自動) / G=実績(入力) / H=差額(=F-G) / I=1人当たり実績(=G/PAX) / J=備考or状態**。**収支サマリーの固定費/変動費合計の参照を実績列（F→G）に更新**。列マッピングを変える改修は「①各行の式②合計行③収支サマリーの参照④make_testの入力列」を必ずセットで直す
  - 2026-07-15 追加: 予算と返金を「予算／実績」2本立てに拡張。**2つの頭数を使い分け**：`PAX=会費負担者（招待・欠席除く）`＝返金・1人当たり実績の分母、`BUDGET_PAX=出席者（招待含む・欠席除く）=CNT_SHAIN+CNT_YAKU+COUNTIF(招待)`＝予算の分母（招待者の食事代・記念品も社員と同じ単価で費用計上し、会費負担者みんなで分担）。収支サマリー・返金配分をF列(予算・見込み)/G列(実績・確定)の2列に再構成（行106→108）。**設定シートの実質負担列は実績返金（G103/G105）を参照**。実績未入力時の過大計算を防ぐガード `=IF(AND(G97=0,G98=0),"",...)` 必須
  - 2026-07-15 追加: 費用の予算入力を「1人当たり予算」と「総額予算」の2列に（記念品・会場費など総額で決まる費用に対応）。予算合計 `G=IF(F<>"",F,IF(E<>"",E*BUDGET_PAX,""))`（総額優先）。費用セクションが**B〜K（10列）に拡張**：E=1人当たり予算/F=総額予算/G=予算合計/H=実績/I=差額/J=1人当たり実績/K=備考or状態。**収支サマリーの参照も予算=G列合計・実績=H列合計にずらす**。両方式・不足/潤沢の各ケースで検証済み
- **学び**:
  - **Windows環境ではxlsxスキルのrecalc.py（LibreOffice方式）が動かない**（`socket has no attribute AF_UNIX`エラー）→ **Excel COM（win32com）方式の再計算スクリプトを自作**。`excel.CalculateFullRebuild()` → `wb.Save()`。scratchに `recalc_excel.py` として保存済み。**tools/へ共通化すると再利用性UP（次回TODO）**
  - **見た目確認**: Excel COMの `ExportAsFixedFormat(0, pdf)` でPDF化 → **PyMuPDF(fitz)で `get_pixmap(dpi=110).save(png)`** して画像化しRead。CopyPicture→Chart.Paste方式は空白になりやすい（クリップボードのタイミング）ので非推奨
  - **既存書式を保った再構築**: 行・列を大幅に増やす改修は、insert_rows/colsより「_styleプロキシを既存代表セルから`copy()`採取 → 旧シート削除 → 同名同indexで再作成 → 採取スタイルで再構築」が確実。**_styleコピーは罫線・塗り・フォント・整形すべて含む。ただし同一wb内でのみ有効**（別wb間はスタイルインデックスがずれてNG）
  - **落とし穴**: スタイル採取元セルの座標を間違えると色が総崩れ（ヘッダー行のセルを入力欄スタイルとして採取してしまい入力欄が青くなった）。**採取元は必ず改修後の最新レイアウトの実セルを指定し、PNG目視で確認**
  - **SUMPRODUCTの空文字エラー**: `=IF(...,"",数値)` を含む列を `SUMPRODUCT((条件)*範囲)` すると文字列×数値で#VALUE!。単純な `SUM()` は文字列を無視するので `=SUM(E7:E46)` が安全
  - **役職別金額はINDEX/MATCH参照**: `=INDEX(設定!$C$14:$C$22,MATCH(D7,設定!$B$14:$B$22,0))` で役職名から金額を引く。IFERRORでフォールバック
  - 元ファイルは上書きせず新バージョン名（_20260714B）で納品。NAS運用ファイルの事故防止
- **2026-07-14 追加：日付セルが数値（シリアル値）で表示される問題と対処**:
  - **原因**: テンプレート再構築時、入力欄を一律同一スタイル（金額用 `#,##0`）でコピーしたため、開催日セルまで金額書式になり日付が `46233` 等のシリアル値で表示された。**入力欄は用途別に書式を分ける**（日付欄・文字欄・金額欄）
  - **落とし穴①**: openpyxlで `cell.number_format='yyyy/m/d'` を設定しても、**その後Excel COMで再計算保存すると書式が `General` や `mm-dd-yy`（米国式）に化ける**。openpyxl経由の日付書式は信頼できない
  - **正解**: **Excel COMの `Range.NumberFormatLocal` で、`CalculateFullRebuild()` の後・`Save()` の直前に設定**すると日本語カスタム書式 `yyyy"年"m"月"d"日"` が確実に保持される（scratchの `set_date_com.py`）。結合セルは範囲全体（`C6:E6`）で指定
  - **落とし穴②**: 日本語Excelで `Range.NumberFormat="General"` はCOM例外（「NumberFormatプロパティを設定できません」）→ `NumberFormatLocal="G/標準"` を使う
  - **落とし穴③**: openpyxlはExcel COMが設定した日本語カスタム書式を読めず `General` と誤表示する。**実表示の検証はExcel COMの `Range.Text` かPDF/PNG目視で行う**（openpyxlのnumber_format読みを信用しない）
  - 運用中ファイルの書式のみ修正するときは、openpyxl保存だと数式キャッシュが消える → **Excel COMで開く→再計算→書式設定→保存**の一連でデータ・キャッシュ・書式すべて保持

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
| 2026/07/10 | plc-debuggerが「また開かない」（2回目の起動不能） | このPCのスタートアップフォルダに自動起動ショートカット未登録（FP7 Diffのみ登録されていた）。install-autostart.batが旧タスクスケジューラ方式のままで、恒久対策（スタートアップフォルダ方式）と矛盾していた | install/uninstall-autostart.batをスタートアップフォルダ方式に書き換え済み。**新PCセットアップ時は各ツールのinstall-autostart.bat実行を必須化** |

---

## インフラ・運用のノウハウ

### GitHub同期（2台PC間）
- SessionStartフックで自動pull、Stopフックで自動commit&push
- push失敗時は.claude/.push_failedに記録、次回起動時に警告
- 本業（work-projects）と副業（my-ai-company）はリポジトリを分離

### セッション健康診断（2026-07-07 my-ai-companyから展開）
- `tools/session_health.py`：コンテキスト使用率 WARN=70% / CRIT=85%、画像 WARN=25枚 / CRIT=40枚
- SessionStart＋Stop両hookで自動実行（`.claude/settings.json`）。正常時は無表示、閾値超過時のみ警告
- 警告が出たらClaudeは作業前に「/compactで圧縮 or 引き継ぎ準備」の2択を提案する（my-ai-company/CLAUDE.mdの容量管理プロトコル準拠）
- 🔴 正本は my-ai-company/tools/session_health.py。改修はそちらで行い、このコピーへ再展開する（二重メンテ禁止）
- 🔴 判定は「実測コンテキスト方式＋transcript_path方式」。旧方式（累計サイズ/入力回数・mtime推測）に戻すと誤報が再発するので戻さない

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
| 2026-05-29 | 生産技術主任補佐PDM | ブラウザツール常駐化の恒久対策パターンを確立（下記） |

---

## ローカルWebツールの「常駐起動」恒久対策（2026-05-29 確立）

### 問題
開発サーバ（vite）を起動して使うツールは、起動したセッション（ターミナル/AIセッション）が
終わるとサーバも一緒に落ちる。「いちいち止まる」と感じる原因。

### 恒久対策（plc-debugger / fp7-diff で実装）
1. **フロントをビルドして固める**: `vite build` → `client/dist`
2. **Express単体で配信**: `NODE_ENV=production` で `client/dist` を静的配信
   ```ts
   if (process.env.NODE_ENV === 'production') {
     app.use(express.static(path.join(__dirname, '../../client/dist')));
     app.get('*', (_req, res) => res.sendFile(path.join(clientDist, 'index.html')));
   }
   ```
   → vite開発サーバが不要になり、プロセスが2個→1個に。ポートも1つで完結（3001 or 3002）
3. **start-production.bat**: `NODE_ENV=production` + `PORT` を設定して `npx tsx src/index.ts`
4. **start-hidden.vbs**: batをウィンドウ非表示で起動（`WshShell.Run "...bat", 0, False`）
5. **スタートアップフォルダにVBSショートカット**: 管理者権限不要でログオン時自動起動
   （タスクスケジューラは管理者権限が必要で `Access denied` になる → スタートアップフォルダが正解）
6. **スマート起動bat（open-*.bat）**: ヘルスチェック→生きてればブラウザを開くだけ／死んでればVBS起動

### 重要な落とし穴
- **batの `timeout /t N` は非対話（非表示）環境で失敗する** → `ping -n N 127.0.0.1 >nul` で代替
- タスクスケジューラ登録は管理者権限必須 → ユーザー権限ならスタートアップフォルダを使う
- ポート設計を分離（plc-debugger=3001 / fp7-diff=3002）すれば複数ツール同時常駐OK

### ポート/URL（本番運用）
- PLC Craft AI: http://localhost:3001
- FP7 Diff: http://localhost:3002

---

## farewell-reception（歓送迎会 当日受付アプリ）2026-07-21 新規作成

- 目的：当日の受付・集金消し込みをスマホで。会費収支Excel（テンプレv3）の参加者33名をD1に取り込んで使用
- 構成：Next.js 16 + @opennextjs/cloudflare + D1 + Cloudflare Access（社内ルール準拠・`preview_urls:false`）
- **学び**：
  - **Next.js 16 は破壊的変更あり**。`node_modules/next/dist/docs/` に**同梱ドキュメント**があり、プロジェクトのAGENTS.mdが「コードを書く前に読め」と指示している。**必ず従う**（Route Handlerは `RouteContext<"/api/xxx/[id]">` 型、`params` は Promise）
  - `npm create cloudflare` の `--framework=next` は **Unsupported でWindowsでクラッシュ**（C3 v2.70.12）→ `create-next-app` で作ってから `@opennextjs/cloudflare` を追加する公式手順が安定
  - `next.config.ts` に `initOpenNextCloudflareForDev()` を書くと `next dev` でもD1バインディングが使える
  - ローカルD1は `wrangler d1 execute <name> --local --file=xxx.sql`。database_id がプレースホルダのままでもローカルは動く
  - **PowerShellツールが EPERM で全滅する事象**が発生（バックグラウンド起動の試行後）。**Bashツールに切り替えれば継続可能**
  - ブラウザ検証で `computer` のクリック座標がずれる／screenshotがタイムアウトする場合、**`javascript_tool` で要素を直接クリックして検証**すると確実
  - 個人情報（氏名・金額）は `.gitignore` に `seed_attendees.sql` `members.json` を追加してコミット防止。**git add後に `git status` で混入チェックする手順を徹底**
- **残作業**：`wrangler login`（人が実行）→ `d1 create` → database_id記入 → `npm run deploy` → **Cloudflareダッシュボードで Access 設定**（未設定だと社外公開になる）

### farewell-reception デプロイ＋Access設定完了（2026-07-22）
- 本番URL: `https://farewell-reception.gp6sk1029.workers.dev`（Cloudflare Workers、D1: c35edf65-...）
- **workers.dev への Cloudflare Access 適用手順**（ブラウザ代行で実施）:
  1. Zero Trust ダッシュ（one.dash.cloudflare.com）→ Access controls → Applications → Create new application
  2. **Self-hosted and private → 「Workers」サブタブ** を選ぶ（workers.dev対応。独自ドメイン不要）
  3. Destinations の Public hostnames で Subdomain=farewell-reception / Domain=gp6sk1029.workers.dev を選択
  4. Access policies → Create new policy → Include: Emails = 許可アドレス、Action=Allow、名前を付けてSave policy
  5. Create でアプリ作成 → 反映後、未認証アクセスは `*.cloudflareaccess.com/cdn-cgi/access/login` へ302
- **検証**: `curl -I <URL>` で 302 + Location が cloudflareaccess.com なら認証OK。アプリHTML（"送別会 受付"等）が見えたら未反映
- **落とし穴**: Cloudфлareダッシュのレンダラが重く、computer screenshotが度々30秒タイムアウト → `wait 3-4秒` 後に再取得、または `read_page`/`find`/`get_page_text` で要素特定すると安定
- ログイン方式は One-time PIN（指定メールにコード送信）。identity provider未設定でもZero Trust Freeで利用可
- **人にしかできない工程**: `wrangler login`（対話）と、実機での初回ログイン（メールOTP入力）は代行不可
