# drawing-checker（ブラウザ版）

SolidWorks 2D図面の自動検図ツール。  
ブラウザでドラッグ&ドロップ → 赤ペン風注釈PDFが表示される。

## クイックスタート

```bash
# 初回セットアップ（依存関係インストール）
start.bat を実行（自動で npm install と pip install が走る）

# 2回目以降
start.bat をダブルクリック
→ http://localhost:5174 が自動で開く
```

## 構成

```
drawing-checker/
├── start.bat / stop.bat     # ワンクリック起動/停止
├── server/                  # Node.js + Express + multer + Python subprocess
│   └── src/
│       ├── index.ts
│       ├── pythonRunner.ts  # Python CLI呼出し
│       └── routes/
│           ├── check.ts     # POST /api/check
│           ├── learn.ts     # POST /api/learn
│           └── files.ts     # GET /api/files/...
│
├── client/                  # React + Vite + Tailwind + react-pdf
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── UploadPanel.tsx
│           ├── ResultPanel.tsx
│           ├── PdfPreview.tsx
│           └── LearnModal.tsx
│
├── src/drawing_checker/     # Python 検図エンジン（CLIとして呼び出される）
├── config/                  # JIS規格ルール・学習ルール
└── requirements.txt
```

## 使い方

### 1. 検図
1. ブラウザでファイルをドロップ（PDF/DXF/DWG/SLDDRW/PNG/JPG）
2. 「検図を実行」をクリック
3. 赤ペン注釈PDF＋指摘一覧が右側に表示される
4. 指摘をクリックするとPDF上の該当箇所がハイライトされる
5. 「注釈PDFを保存」でダウンロード

### 2. サンプル学習（社内ルール自動生成）
1. ヘッダー右の「🎓 サンプル学習」をクリック
2. 合格図面を5〜10枚ドロップ
3. 「学習を開始」→ `config/learned_rules.json` が生成される
4. 以降の検図はJIS規格＋社内ルールの両方で判定

### 3. AI補完レイヤー
チェックボックス「Gemini AI補完レイヤー」をONにすると、ルールでは拾えない違和感を検出します（APIコスト発生）。`.env` の `GEMINI_API_KEY` を設定してください。

## API

| メソッド | パス | 用途 |
|---|---|---|
| GET | `/api/health` | 生存確認 |
| GET | `/api/info` | JIS/学習ルール件数 |
| POST | `/api/check` | 検図実行（form-data: file, ai） |
| POST | `/api/learn` | サンプル学習（form-data: files[], noAi） |
| GET | `/api/files/result/:id/:name` | 結果PDF取得 |

## 詳細はSKILL.md参照
