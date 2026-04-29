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
