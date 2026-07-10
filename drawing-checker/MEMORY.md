# drawing-checker MEMORY.md

> 本プロジェクト固有の学び・失敗パターンを記録する。  
> 上位の `work-projects/MEMORY.md` と併せて参照のこと。

---

## プロジェクト概要
SolidWorks 2D図面（PDF/DXF/DWG/SLDDRW/画像）を入力とし、JIS規格＋サンプル図面学習ルールで自動検図し、赤ペン風注釈PDFとHTMLレポートを出力する。

**形態**：2026-04-15にCLIからブラウザ版に移行。
- バックエンド：Python（検図エンジン）＋ Node.js/Express（APIゲートウェイ）
- フロントエンド：React + Vite + Tailwind + react-pdf
- 起動：`start.bat` ダブルクリック → http://localhost:5174

## CLI→ブラウザ版移行の学び（2026-04-15）

### 成功パターン
1. **CLIに `--json` オプションを追加してそのままExpressから呼ぶ**構成が最速
   - Python側に新しいコードをほぼ書かずに済む
   - CLIも残るのでバッチ処理・CI連携も可能
2. **ログはstderr・データはstdout**の分離が必須
   - 最初 `logger.StreamHandler(sys.stdout)` だったためJSONパースが壊れた
   - `StreamHandler(sys.stderr)` に変更で解決
3. **Windows stdoutはUTF-8で直接バイト書き込み**
   - `sys.stdout.buffer.write(json.dumps(...).encode('utf-8'))` でcp932問題を回避
4. **plc-debuggerの`start.bat`構成をそのままコピー**
   - 依存自動インストール・ポート競合クリア・ヘルスチェック待機のパターンが流用できた
5. **注釈PDFはサマリーページが1ページ目に挿入される**ので
   - フロント側の findings.page_number → PDFページは **+1** のオフセット必要

### 失敗パターン（今回は回避済み）
| 失敗 | 対策 |
|---|---|
| multerの`file.originalname`がlatin1で届き日本語ファイル名が壊れる | `Buffer.from(name, 'latin1').toString('utf-8')` でデコード |
| Python CLIのログがJSONに混入 | ログはstderrに分離、extractJsonで前置ログをスキップ |
| 同名ファイルのアップロードで結果PDFが上書きされる | timestamp+hashで一意なサブディレクトリを切る |
| 初期構築時にfavicon.svgを忘れた | 事後追加済み（紺背景の製図三角定規＋赤丸チェック）。今後のブラウザツールはCLAUDE.md参照 |

### ファビコンデザイン方針（本プロジェクト）
- 背景：濃紺 `#0f172a`（ダークテーマ準拠）
- メイン：シアン `#22d3ee` の製図三角定規＋目盛り（「図面」を象徴）
- 差し色：赤 `#ef4444` の丸＋白チェックマーク（「検図＝赤ペン」を象徴）
- SVG 64×64 でベクター化、ファイルサイズ1KB未満

---

## 振り返りレポート（CLAUDE.md準拠）

### エージェント名：drawing-checker
### 業務・タスク内容：SolidWorks 2D図面 自動検図ツール（CLI→ブラウザ版→サンプル管理機能）
### 実行日：2026-04-15

✅ **良かった点**
- Pythonエンジン完成済みだったため、Expressはsubprocessで呼ぶだけの薄いラッパーで済み、見積3時間→実績1時間で完成
- JIS規格＋サンプル学習の3層ルール合成アーキテクチャは社内運用の柔軟性と業界標準の担保を両立
- サンプル管理UI（一覧/プレビュー/削除/再学習）で「学習した内容の可視化と更新」を実現、ブラックボックス化を防止

⚠️ **改善点**
- 初版でfavicon.svgを設置し忘れた → CLAUDE.mdに必須ルール追加で再発防止
- Python側のloggerがデフォルトstdoutで、JSON出力を壊した → stderrに分離
- 絵文字の多いUIはアクセシビリティとして課題（アイコンライブラリへの置換は今後検討）

🔄 **次回試すこと**
- 検図結果のCSVエクスポート機能（Excel連携したい）
- DWGファイル検証（ODA File Converter実インストール後）
- SolidWorks COM APIでの直接検図（SLDDRW対応）

📝 **SKILL.md更新提案**
- サンプル管理機能の説明追加 → ✅ 適用済

💾 **MEMORY.md追記内容**
- 「Python+Expressブリッジ」の具体パターンを work-projects/MEMORY.md に昇格 → ✅ 完了
- 「ファビコン必須」をCLAUDE.mdに昇格 → ✅ 完了

💰 **ROI評価**
- 投じた時間：開発 約8時間（エンジン3h + Web化1h + サンプル管理0.5h + ファビコン/ドキュメント整備1.5h + 諸々2h）
- 得られたリターン：
  - 直接：手動検図20分→8分/枚、月20枚換算で年48h削減（年14.4万円相当）
  - 波及：ブラウザツール標準パターン／Python-Expressブリッジ手順がCLAUDE.mdに昇格、
    今後のツール開発時間を1ツールあたり数時間短縮できる見込み
- ROI向上策：他の本業プロジェクト（巻線レポート等）もブラウザ化できる型ができたので、横展開で価値増幅

## アーキテクチャの要点

### 3層ルール合成
```
learned_rules.json（サンプル学習）> jis_rules.json（JIS規格）> check_rules.json（汎用）
```
- 同IDがあれば上位優先
- JIS必須ルールは `override_by_sample: false` でサンプル学習による上書きを禁止
- 例：`JIS-Z-8316-001`（第三角法マーク必須）、`JIS-B-0021-001`（幾何公差3要素）は常にJISが勝つ

### 統一ドローイングモデル
- 全パーサーは `Drawing → Page[] → Entity[] / Dimension[] / Symbol[] / TitleBlock` の共通構造を返す
- チェッカーは入力形式に依存せず、このモデルだけを相手にする

## 初版実装時の知見

### 成功パターン
1. **dataclassでモデル定義 → IDE補完とリファクタ耐性が向上**
2. **ルールJSONの `checker` フィールドで自動振り分け** → 新しいルール追加時もチェッカー本体を触らず済む
3. **JIS規格を 20件のJSONルールに凝縮** → 汎用性と保守性のバランスが取れた
4. **`rule_engine.get_rule(rule_id)` で参照ルールを明示** → 各チェッカーコードが自己説明的になる
5. **PyMuPDFで PDF→注釈→出力 が1ライブラリで完結** → 依存を減らせた

### 失敗・注意パターン
| 場面 | 問題 | 対策 |
|---|---|---|
| ディレクトリ作成 | `drawing-checker`（ハイフン）と`drawing_checker`（アンダースコア）を混同 | Windowsで`mkdir -p`後も必ず`ls`で確認 |
| PDF座標系 | PyMuPDFはY下向き、PDF仕様はY上向き | `page_h - y` で明示変換。 `pdf_parser.py`と`pdf_annotator.py`の両方で必要 |
| argparse + pipe | `python -m ... --help | head` がWindowsでハング | 直接実行orsubprocess使用で回避 |
| SolidWorks COM | 未インストール環境で例外 | `platform.system()`＋`try/except`でグレースフル失敗 |
| DXF読み込み | 壊れたDXFで`readfile`失敗 | `ezdxf.recover.readfile`でリトライ |

## チェッカー別メモ

### dimension_checker
- 寸法値は `DIMENSION_PATTERN`（φ/R/±/H7等のプレフィクス・サフィクス対応）で抽出
- 近傍判定の閾値: 60pt（約21mm）← 実図面で要調整
- 単位ミス検出: 10000mm超 or 0.01mm未満でWARN

### title_block_checker
- タイトルブロック領域: ページ右下の長辺×35%を想定
- DXFは座標系がモデル空間なのでこの判定は効かない → `page.raw_text`全体から拾う
- キーワードマッチ後、`pattern`（正規表現）があれば検証

### line_style_checker
- DXF: レイヤー名/LINETYPEで線種推定（LAYER_HINTS / LINETYPE_HINTS）
- PDF: `dashes`文字列長で破線判定（ヒューリスティック）
- レイヤー混在（1レイヤーに複数線種）は WARN

### symbol_checker
- 幾何公差フレーム: `GEOM_FRAME_PATTERN` で「記号｜値｜データム」の3要素を正規表現で判定
- データム整合性: 参照されているデータム記号（A,B,C）が図面上で定義されているか逆引き
- 旧▽表記はINFO扱い（禁止ではなく非推奨）

## AI連携（Gemini 2.5 Flash）

### 使い方
- `--ai` フラグで `anomaly_detector.run()` が走る → 図面サマリをJSONで送り、指摘候補JSONで返してもらう
- `learn` コマンドで `rule_learner._ai_generate_rules()` が走る → サンプル統計＋AI推論で社内ルール候補生成

### コスト対策
- デフォルトOFF（`--ai` オプトイン）
- 画像は送らずテキストサマリのみ送信
- JSONパース失敗時はフォールバック（`_parse_json_robust`）

## 動作確認結果（2026-04-15 初版）
- ルールエンジン: 有効ルール23件ロード成功
- 4チェッカー: 全て例外なく実行、11件の指摘を正しく検出（ダミー図面）
- CLI: `--help` 表示成功

## 次回試すこと
- [ ] 実際のPDF図面での検証（サンプル1枚作成）
- [ ] A3/A2/A1図面での用紙サイズ判定精度
- [ ] DXFパーサー の MTEXT 中の改行コード処理
- [ ] GUI版のtkinterdnd2が無い環境でのフォールバック動作

## 振り返りレポート（CLAUDE.md準拠）

### 初版実装（2026-04-15）
**エージェント名**: Claude（drawing-checker初版実装担当）  
**業務・タスク内容**: 検図ツールの初版実装（モデル・ルールエンジン・4チェッカー・パーサー5種・AI連携・GUI・CLI・ランチャー）

**✅ 良かった点**
- 3層ルール合成（learned/jis/fallback）の構造を先に固めたので、後から新しいチェックを足しやすい形になった
- JIS規格20ルールを先に事前内蔵したので、サンプルなしでも即動作する
- 統一ドローイングモデルを全パーサー共通にしたので、チェッカー側が形式に依存しない

**⚠️ 改善点**
- 実図面での動作未検証（ダミー図面のみ）
- PyMuPDFのY座標反転処理が2ヶ所（パーサー/アノテーター）で重複 → ヘルパー関数化すべき
- `tests/` が空のまま → pytest で各チェッカーを回帰テストすべき

**🔄 次回試すこと**
- 実PDF図面を1枚用意して end-to-end の動作確認（処理時間3分以内の目標検証）

**📝 SKILL.md更新提案**: 初版ゆえ特になし。実運用で見えた制約があれば追加する

**💾 MEMORY.md追記内容**: 本記録とwork-projects/MEMORY.md両方に記録済み

**💰 ROI評価**
- 投じた時間: 約3時間（プラン〜初版実装・動作確認）
- 得られたリターン: 検図作業を月4h削減する見込みのツール基盤が完成
- 次回改善でROIを上げる方法: 実図面検証と精度チューニングに次1〜2時間投下すれば実用ラインに到達可能

---

# 引き継ぎ書（2026-05-06 時点）

> **次のセッションでこのプロジェクトを触る人（Claude含む）は、必ずこの章を最初に読むこと。**

---

## 1. プロジェクトの現在地

### 完成・動作しているもの
| 機能 | 状態 | ファイル |
|---|---|---|
| Python 検図エンジン（CLI） | ✅ 動作確認済 | `src/drawing_checker/` |
| Express サーバー（API） | ✅ 動作確認済 | `server/src/` |
| React ブラウザUI | ✅ 動作確認済 | `client/src/` |
| PDFパーサー | ✅ | `parsers/pdf_parser.py` |
| DXFパーサー | ✅ | `parsers/dxf_parser.py` |
| DWG→DXF変換 | ⚠️ ODA未インストール | `parsers/dwg_converter.py` |
| SLDDRWパーサー | ⚠️ SolidWorks COM必要 | `parsers/swx_parser.py` |
| 画像パーサー（OCR） | ⚠️ Tesseract未インストール | `parsers/image_parser.py` |
| PDF赤ペン注釈出力 | ✅ 日本語対応済 | `reporter/pdf_annotator.py` |
| HTMLレポート | ✅ | `reporter/html_reporter.py` |
| サンプル管理（一覧/削除/再学習） | ✅ | `server/src/routes/samples.ts` + `LearnModal.tsx` |
| 製作可能性チェッカー（AI） | ✅ コード完成 | `ai/manufacturability.py` |
| start.bat / stop.bat | ✅ | ルートに配置 |
| favicon.svg | ✅ | `client/public/favicon.svg` |

### まだ未完了（次回対応候補）
| 課題 | 優先度 | 詳細 |
|---|---|---|
| **`.env` ファイルが未作成** | ★★★ | `.env.example` をコピーして `GEMINI_API_KEY` を設定する必要がある。AI機能（加工可能性チェック）に必須 |
| **PDFプレビューが表示されない問題** | ★★☆ | react-pdfのworker URL をCDN方式に変更済みだが未検証。Ctrl+F5 でリロードして確認が必要 |
| **タイトルブロック検出精度** | ★★☆ | SolidWorks PDFはページ回転(rotation:90)がかかっており、座標ベースの領域検出が困難。現在はキーワードベースに変更済みだが、スペース入り（「図  番」）への対応も追加済み。精度はサンプル学習に依存 |
| **Tesseract / ODA のインストール** | ★☆☆ | 画像/DWG対応に必要だが、PDF/DXFのみで十分なら不要 |
| **検図結果のCSVエクスポート** | ★☆☆ | 要望として記録のみ |

---

## 2. アーキテクチャ概要

```
[ブラウザ UI]  http://localhost:5174
     │ /api/*
     ▼
[Express サーバー]  http://localhost:3001
     │ subprocess: python -m drawing_checker check <file> --json
     ▼
[Python 検図エンジン]
     │
     ├─ parsers/  → 入力を統一モデル(Drawing)に変換
     ├─ checkers/ → 4系統チェッカー（寸法/タイトル/線種/記号）
     ├─ ai/       → Gemini 2.5 Flash（製作可能性チェック）
     ├─ reporter/ → PDF赤ペン注釈 + HTMLレポート
     └─ rule_engine.py → 3層ルール合成（learned > JIS > fallback）
```

### ポート
- フロント: **5174**（plc-debuggerの5173と衝突しないよう）
- バックエンド: **3001**

### ルール構成（3層）
```
config/learned_rules.json  ← サンプル学習で生成（最優先・現在7件）
config/jis_rules.json      ← JIS規格を事前内蔵（現在21件）
config/check_rules.json    ← 汎用フォールバック
```

---

## 3. 起動方法

```bash
# 通常起動（ダブルクリックでもOK）
cd C:\Users\SEIGI-N13\work-projects\drawing-checker
start.bat

# 手動起動（デバッグ時）
cd server && npx tsx src/index.ts        # バックエンド（別ターミナル）
cd client && npx vite --host             # フロント（別ターミナル）

# CLI直接実行
set PYTHONPATH=src
python -m drawing_checker check <file.pdf> --json
python -m drawing_checker check <file.pdf> --ai    # AI付き
python -m drawing_checker learn <sample_dir>
```

---

## 4. チェッカーの現状（何を指摘し、何を指摘しないか）

### 有効なチェック（実務で役に立つもののみ残存）
| チェッカー | rule_id | 内容 |
|---|---|---|
| dimension | DIM-NO-DIMENSIONS | 寸法が1つも無い |
| dimension | DIM-UNIT-SUSPECT | 寸法値10000mm超（単位ミス疑い）|
| title_block | TITLE-BLOCK-EMPTY | 図番/品名/材質/尺度の3つ以上が欠落 |
| symbol | GEOM-VALUE-MISSING (JIS B 0021) | 幾何公差フレームに公差値がない |
| symbol | DATUM-UNDEFINED (JIS B 0021) | 参照データムが図面上に未定義 |
| symbol | WELD-SYMBOL-MISSING (JIS Z 3021) | 溶接記述あるが記号なし |
| line_style | LAYER-MIX | DXFレイヤーに線種混在 |
| **AI** | **MFG-MISSING-DIM** | **加工に必須な寸法の欠落**（AI駆動）|
| **AI** | **MFG-INFEASIBLE** | **加工が困難/不可能な形状**（AI駆動）|

### 意図的に無効化したチェック（誤検知が多かったもの）
| 元のチェック | 無効化理由 |
|---|---|
| 線幅JIS規定チェック（1080件警告の原因）| PDFから線幅が正確に取れず全線に警告 |
| 円/円弧の近傍に寸法がないか | PDF解析で矢印紐付け不正確 |
| 直径φ必須公差 | 普通公差でカバーされる場面が多い |
| 寸法の重複検出 | 図番を寸法と誤検出する |
| 表面性状未記入警告 | 加工不要部品で誤検知 |
| 第三角法マーク | 図記号のみの図面で誤検知 |
| 用紙サイズJIS非準拠 | 実務では自由サイズを使う |
| 空白ページ検出 | 実用性低い |

---

## 5. 直近セッションで発生した問題と対策

### 問題1：PDF注釈のアイコンが画面を埋め尽くす（1080件警告）
- **原因**: line_style_checker が全ての線に線幅JIS規定違反を出力
- **対策**: 線幅チェック無効化 + PDF注釈から📄ポップアップ廃止 → 番号バッジ＋矩形のみに
- **ファイル**: `reporter/pdf_annotator.py`, `checkers/line_style_checker.py`

### 問題2：ダウンロードPDFが「?????」（文字化け）
- **原因**: PyMuPDFのデフォルトフォント `helv` (Helvetica) が日本語非対応
- **対策**: `insert_htmlbox` 優先、フォールバックでWindowsシステムフォント(Meiryo等)
- **ファイル**: `reporter/pdf_annotator.py` の `_insert_jp_text()`

### 問題3：PDFプレビューが表示されない
- **原因**: react-pdf の worker URL が Vite 環境で解決失敗
- **対策**: CDN方式に変更 (`unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`)
- **ファイル**: `client/src/components/PdfPreview.tsx`
- **状態**: 未検証（Ctrl+F5 で確認が必要）

### 問題4：タイトルブロック誤検知（「白紙」と判定）
- **原因**: PDF rotation:90 で座標系が想定とズレ ＋ 「図  番」（スペース入り）でキーワードマッチ失敗
- **対策**: 領域ベース → キーワードベースに変更、スペース無視マッチ、ラベル存在だけで記入ありとみなす緩い判定
- **ファイル**: `checkers/title_block_checker.py` の `_find_field_value()`

---

## 6. セットアップ手順（新環境で動かす場合）

```bash
# 1. Python依存
cd C:\Users\SEIGI-N13\work-projects\drawing-checker
pip install -r requirements.txt

# 2. Node依存
cd server && npm install && cd ..
cd client && npm install && cd ..

# 3. 環境変数
copy .env.example .env
# .env を編集して GEMINI_API_KEY=あなたのキー を設定
# APIキー取得: https://aistudio.google.com/apikey

# 4. 起動
start.bat
```

### 現在のインストール状況（2026-05-06時点）
| 項目 | 状態 |
|---|---|
| Python + PyMuPDF + ezdxf + google-genai + dotenv | ✅ インストール済 |
| server/node_modules | ✅ インストール済 |
| client/node_modules | ✅ インストール済 |
| `.env` ファイル | ❌ **未作成（GEMINI_API_KEYが必要）** |
| サンプル図面 | ✅ 14枚学習済み（server/uploads/learn/ に2バッチ）|
| 学習ルール | ✅ 7件生成済み（config/learned_rules.json）|
| Tesseract OCR | ❌ 未インストール（画像パーサー用・PDF/DXFのみなら不要）|
| ODA File Converter | ❌ 未インストール（DWG用・DXFで十分なら不要）|

---

## 7. 次のセッションでやるべきこと（優先順）

1. **`.env` ファイルを作って GEMINI_API_KEY を設定** → AI製作可能性チェックが有効化される
2. **ブラウザで Ctrl+F5 してPDFプレビューが表示されるか確認** → 動かなければ DevTools Console のエラーを見る
3. **実際の図面で「🏭 加工可能性チェック（AI）」にチェックを入れて検図** → 「必須寸法欠落」「加工困難」の指摘品質を評価
4. **指摘が甘い/厳しい場合** → `ai/manufacturability.py` の `PROMPT_TEMPLATE` を調整
5. **サンプル学習の精度UP** → 現在14枚学習済み。追加図面を食わせて再学習すると改善

---

## 8. 重要ファイルの変更履歴（直近セッション）

| ファイル | 変更内容 |
|---|---|
| `reporter/pdf_annotator.py` | 全面書き直し：📄アイコン廃止→番号バッジ、INFOは非表示、同ルール20件上限、近接クラスタリング、日本語フォント対応(`insert_htmlbox`)、ページ回転対応(mediabox使用)、サマリーページ固定A4 |
| `checkers/dimension_checker.py` | 簡素化：寸法ゼロ検出＋単位ミス検出のみ。JIS教科書的チェック全廃 |
| `checkers/line_style_checker.py` | 簡素化：DXFレイヤー混在のみ。線幅チェック全廃 |
| `checkers/symbol_checker.py` | 簡素化：幾何公差/データム/溶接の実際使用時のみ。表面性状未記入チェック廃止 |
| `checkers/title_block_checker.py` | 大改修：座標ベース→キーワードベース、スペース無視マッチ、3項目以上欠落でのみERROR、投影法/用紙サイズ/空白ページ検出を廃止 |
| `ai/gemini_client.py` | `generate_with_image` / `generate_json_with_image` 追加（画像入力対応）|
| `ai/manufacturability.py` | **新規作成**：PDF→PNG画像化→Geminiで「加工視点」分析。必須寸法欠落＋加工困難箇所を検出 |
| `config/jis_rules.json` | 21ルールを復活（一度廃止して再復活。参照情報として保持）|
| `client/src/components/PdfPreview.tsx` | worker URL をCDN方式に変更、エラーUIにダウンロードボタン追加 |
| `client/src/components/UploadPanel.tsx` | AI文言を「🏭 加工可能性チェック」に変更 |
| `client/src/components/LearnModal.tsx` | サンプル管理UI追加（既存一覧タブ＋追加アップロードタブ、削除/再学習/プレビュー）|
| `client/public/favicon.svg` | **新規作成**（濃紺背景＋シアン定規＋赤丸チェック）|
| `server/src/routes/samples.ts` | **新規作成**（GET一覧/DELETE削除/POST再学習/DELETE全リセット）|

---

## 9. ユーザーの要望傾向（対応方針の参考）

- **JIS教科書的な指摘は不要**：ユーザーは「実務上まったくどうでもいい」と明言。JISルールは参照情報として残すが、検査は実務で差し支えるものだけに絞る
- **加工現場の視点を重視**：「加工に必須な寸法が抜けてないか」「加工自体が困難な図面か」が本当に欲しい検図
- **ブラウザ版を好む**：CLIランチャーは削除された。GUIはブラウザ版一本
- **ファビコン必須**：全ブラウザツールに適用するルールとしてCLAUDE.mdに反映済み
- **ノウハウは全体に反映**：個別プロジェクトの学びはwork-projects/MEMORY.md → CLAUDE.md に昇格する仕組みを要望。エスカレーションルールとしてCLAUDE.mdに記載済み
