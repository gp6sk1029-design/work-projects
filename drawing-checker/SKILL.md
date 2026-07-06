# drawing-checker（SolidWorks 2D図面 検図ツール）

## 概要
SolidWorksから2D化した図面（PDF/DXF/DWG/SLDDRW/PNG/JPG）を自動検図し、赤ペン風の注釈を直接書き込んだPDFを出力するツール。
サンプル図面から社内ルールを学習し、JIS規格と組合せて判定する。

## 使い方

### 基本：ブラウザ版（推奨）
```
start.bat をダブルクリック
→ http://localhost:5174 が自動で開く
→ 図面をドロップ → 「検図を実行」
→ 赤ペン注釈PDF + 指摘一覧が表示される
```

### CLI版（バッチ処理向け）
```bash
# ファイル指定
python -m drawing_checker check <input_file>
  → 同じディレクトリに <name>_checked.pdf と report.html が出力される

# ディレクトリ一括
python -m drawing_checker check <directory>

# AI補完レイヤーを有効化（違和感検出）
python -m drawing_checker check <input_file> --ai

# カスタムルール指定
python -m drawing_checker check <input_file> --rules config/my_rules.json

# JSON出力（Web連携用）
python -m drawing_checker check <input_file> --json --no-pdf --no-html
```

### サンプル学習モード
```
ブラウザ版：ヘッダー右の「🎓 サンプル学習」→ 合格図面を複数ドロップ

CLI版：
  python -m drawing_checker learn <sample_dir>/*.pdf
  → config/learned_rules.json が生成される
```

## 対応形式

| 形式 | 解析方式 | 精度 | 備考 |
|---|---|---|---|
| PDF | PyMuPDF | ★★★★★ | テキスト・ベクター情報で最も正確 |
| DXF | ezdxf | ★★★★★ | 構造化データで寸法/線/文字が取れる |
| DWG | ODA File Converter→DXF | ★★★★☆ | ODA CLI要インストール |
| SLDDRW | SolidWorks COM API | ★★★☆☆ | SolidWorks本体が必要 |
| PNG/JPG | OpenCV + Tesseract OCR | ★★☆☆☆ | 最終手段 |

## チェック項目

| チェッカー | 対象 |
|---|---|
| dimension_checker | 寸法記入漏れ・公差の妥当性（JIS B 0401/B 0405準拠） |
| title_block_checker | 図枠・タイトルブロック記入漏れ（JIS Z 8311準拠） |
| line_style_checker | 線種・線の太さ・投影法整合性（JIS Z 8114/Z 8316準拠） |
| symbol_checker | 表面粗さ・幾何公差・溶接記号（JIS B 0601/B 0021/Z 3021準拠） |

## ルール合成の優先順位

```
[1] learned_rules.json（サンプル図面から学習）← 最優先
[2] jis_rules.json（JIS規格を事前内蔵）
[3] check_rules.json（汎用フォールバック）
```
- `jis_rules.json`で`override_by_sample: false`のルールはサンプル学習で上書き不可（JIS必須項目）

## 設定ファイル

### .env
```
GEMINI_API_KEY=your_api_key_here
ODA_CONVERTER_PATH=C:/Program Files/ODA/ODAFileConverter/ODAFileConverter.exe
TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe
```

### config/jis_rules.json
JIS規格に基づく必須ルール（10規格）を事前内蔵。編集非推奨。

### config/learned_rules.json
`learn`コマンドで自動生成される社内固有ルール。手動編集可能。

## 事前セットアップ

1. Python 3.10以上
2. `pip install -r requirements.txt`
3. ODA File Converter（DWG対応時）: https://www.opendesign.com/guestfiles/oda_file_converter
4. Tesseract OCR + 日本語データ（画像対応時）
5. `.env.example`をコピーして`.env`を作成し、GEMINI_API_KEYを設定

## ファイル構成

```
drawing-checker/
├── SKILL.md / README.md / MEMORY.md
├── start.bat / stop.bat      # ブラウザ版起動/停止
├── requirements.txt
├── .env.example / .gitignore
│
├── config/                   # ルール定義
│   ├── check_rules.json      # 汎用フォールバック
│   ├── jis_rules.json        # JIS規格（21ルール）
│   ├── title_block_templates.json
│   ├── tolerance_table.json
│   └── learned_rules.json    # サンプル学習で生成（.gitignore）
│
├── src/drawing_checker/      # Python 検図エンジン
│   ├── main.py               # CLIエントリポイント（--json 対応）
│   ├── model.py
│   ├── rule_engine.py
│   ├── parsers/              # PDF/DXF/DWG/SLDDRW/画像
│   ├── checkers/             # 4系統チェッカー
│   ├── ai/                   # Gemini連携・学習
│   ├── reporter/             # PDF注釈・HTMLレポ
│   └── utils/
│
├── server/                   # Node.js + Express
│   └── src/
│       ├── index.ts
│       ├── pythonRunner.ts   # Python CLI呼出し
│       └── routes/check.ts, learn.ts, files.ts
│
├── client/                   # React + Vite + Tailwind + react-pdf
│   └── src/
│       ├── App.tsx
│       ├── components/UploadPanel.tsx, ResultPanel.tsx,
│       │               PdfPreview.tsx, LearnModal.tsx
│       └── types/
│
└── tests/samples/            # .gitignore
```

## 注意事項

- `samples/` および `*_checked.pdf` は.gitignoreで除外（機密図面の漏洩防止）
- GEMINI_API_KEYはコミット禁止。`.env`は.gitignoreに含まれている
- AI補完レイヤー（`--ai`）はAPIコストが発生する。デフォルトはOFF
- SolidWorks COM APIはSolidWorksがインストールされたPCでのみ動作
- DWGサポートはODA File Converterの別途インストールが必要

## 自己改善ループ（CLAUDE.mdに準拠）

このエージェントはCLAUDE.mdの方針に従い、
タスク完了のたびに振り返りレポートを出力し、
SKILL.mdとMEMORY.mdを更新し続ける。
ROI評価を毎回行い、費用対効果を最大化する。

### ROI試算
| 項目 | 数値 |
|---|---|
| 手動検図（現状） | 20分/枚 × 月20枚 = 月 6.7h |
| ツール使用後 | 8分/枚（自動3分+人確認5分） = 月 2.7h |
| 削減時間 | 月 4h／年 48h |
| 時給3000円換算 | 年 14.4万円の価値 |
| 回収期間 | 約5ヶ月 |
