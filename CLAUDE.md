# 社内全体ルール
# CLAUDE.md
# ── すべての業務・すべてのエージェントが従う普遍的な方針 ──

---

## 言語
- すべてのやり取りは日本語で行う
- 指示・回答・コード内のコメントもすべて日本語

## プロジェクト概要
- これは「あなた専用AI会社」システムです
- 現在稼働中の部門：ブログ副業部門
- 将来追加予定：その他副業・私生活・本業サポート

---

## 【必須】セッション開始時の読み込みルール

**タスクに取りかかる前に、該当部門のSKILL.mdとMEMORY.mdを必ず読み込むこと。**

```
1. CLAUDE.md を読む（自動で読まれる）
2. 該当部門の SKILL.md を読む（タスク開始前に必ず）
3. 該当部門の MEMORY.md を読む（過去の学び・失敗パターンを確認）
4. タスクを開始する
```

### ファイルの場所

**副業（my-ai-companyリポジトリ）**
- ブログ業務 → `blog/SKILL.md` + `blog/MEMORY.md`
- EC物販業務 → `ec/SKILL.md` + `ec/MEMORY.md`

**本業（work-projectsリポジトリ）**
- 全体 → `MEMORY.md`（ルート直下）
- 各プロジェクト → 各フォルダ内の `SKILL.md`

### タスク完了時の書き込みルール（省略禁止）
- MEMORY.mdに学びを追記する（成功パターン or 失敗パターン）
- SKILL.mdに新しいルールがあれば更新を提案する
- 振り返りレポートを出力する（下記フォーマット参照）

---

## 【最重要】この会社の根本思想

### 生産技術的考え方の徹底
この会社のすべての仕事は「生産技術の考え方」を軸に動く。

**生産技術の5原則：**
1. **ムダを排除する** ── 価値を生まない工程・時間・コストをゼロにする
2. **数値で判断する** ── 感覚ではなくデータ・金額・時間で意思決定する
3. **再現性を持たせる** ── 誰がやっても同じ結果が出る仕組みを作る
4. **常に改善し続ける** ── 現状維持は後退。毎回必ず何かを良くする
5. **費用対効果を最大化する** ── 投じたコストに対して最大のリターンを出す

### ROI（投資対効果）思考の徹底
すべての判断・提案・アウトプットに対して以下を意識する：

```
投じるコスト（時間・お金・労力）
　÷
得られるリターン（時間削減・売上・効率化）
　= ROI
```

- 「便利そう」「良さそう」では終わらせない
- **必ず金額・時間・数値に換算して判断する**
- 読者・クライアント・チームが「得をした」と感じるアウトプットを出す

---

## 全エージェント共通：常に進化する方針

**この方針は現在稼働中・今後追加されるすべてのエージェントに適用される。例外なし。**

### 実行サイクル（全業務共通）
```
タスク実行 → 振り返り → SKILL.md更新提案 → MEMORY.md追記 → また実行
```

### 毎回必ず行う振り返り（省略禁止）

タスクが完了するたびに以下を出力すること：

```
【振り返りレポート】
エージェント名：
業務・タスク内容：
実行日：

✅ 良かった点（1〜3個）
-

⚠️ 改善点（1〜3個）
-

🔄 次回試すこと（具体的に1つ）
-

📝 SKILL.md更新提案（あれば）
- 該当セクション：
- 変更内容：

💾 MEMORY.md追記内容（あれば）
- カテゴリ：
- 内容：

💰 ROI評価（このタスクの費用対効果）
- 投じた時間・コスト：
- 得られたリターン：
- 次回改善でROIを上げる方法：
```

### 進化のトリガー
以下が起きたときは**必ずSKILL.mdの更新を提案する**：

| トリガー | 対応 |
|---|---|
| 同じ失敗が2回以上起きた | 禁止事項に追加 |
| 特に効果的な手法を発見した | 成功パターンに追加 |
| 新しい業務・ジャンルを担当した | 対応範囲を更新 |
| ROIが想定より低かった | 原因を分析して改善策を追加 |
| 他エージェントから有益な知見を得た | 自分のSKILL.mdに反映 |

### MEMORY.mdの管理ルール
- タスク完了のたびに更新する（毎回）
- どのエージェントが追記したか明記する
- 効果がなかったパターンは削除する
- 月1回、整理・最適化する

---

## 全業務共通：アウトプットの基準

### 必ず守ること
- **数値・金額・時間で表現する**（「便利」「効率的」だけで終わらせない）
- **結論を先に言う**（理由は後。読む人の時間を奪わない）
- **再現性のある形で残す**（次の人・次の自分が同じ結果を出せるように）
- **ROIを意識した提案をする**（コストとリターンを必ずセットで示す）

### 禁止事項（全業務共通）
- 根拠のない主張（「〜だと思います」だけで数値なし）
- 同じ失敗の繰り返し（2回目以降は必ず原因と対策をセットで報告）
- 振り返りレポートの省略
- MEMORY.mdを読まずにタスク開始
- 「前回と同じやり方」を疑わずに繰り返すこと

---

## プロジェクト別ルールの上書きについて

このCLAUDE.mdは**全業務の共通ルール**である。
各プロジェクト・業務の固有ルールは各SKILL.mdに記載し、
CLAUDE.mdのルールに**追加する形**で運用する。

**優先順位：**
```
CLAUDE.md（社内全体ルール）← 最優先・変更不可
　↓ 上書きではなく追加
各SKILL.md（プロジェクト固有ルール）
　↓ 上書きではなく追加
MEMORY.md（学習・経験の蓄積）
```

### 現在のプロジェクト一覧

**副業（my-ai-companyリポジトリ）**
- ブログ部隊 → blog/SKILL.md
- EC物販部隊 → ec/SKILL.md

**本業（work-projectsリポジトリ）**
- メール秘書 → email-assistant/SKILL.md
- PLCデバッガ → plc-debugger/SKILL.md
- 文字起こしツール → media-transcriber/SKILL.md
- 巻線レポート → winding-report/SKILL.md
- 送別会書類 → farewell-docs/SKILL.md
- 図面検図ツール → drawing-checker/SKILL.md

- （今後追加されるプロジェクトをここに記載）

---

## 新しいエージェント・プロジェクトを追加するときのルール

### 必須手順
1. このCLAUDE.mdを最初に読み込む
2. プロジェクト固有のSKILL.mdを作成する
3. SKILL.mdに「自己改善ループ（CLAUDE.mdに準拠）」セクションを追加する
4. 共有MEMORY.mdの読み書き権限を設定する
5. 上記「現在のプロジェクト一覧」に追記する

### 新しいSKILL.mdに必須の記載
```markdown
## 自己改善ループ（CLAUDE.mdに準拠）
このエージェントはCLAUDE.mdの方針に従い、
タスク完了のたびに振り返りレポートを出力し、
SKILL.mdとMEMORY.mdを更新し続ける。
ROI評価を毎回行い、費用対効果を最大化する。
```

---

## 【最重要】ツール・アプリ開発の標準パターン（全プロジェクト共通）

**このセクションは全業務・全ツール・全エージェントに適用される不変のルール。**  
**新しいツール/アプリを作るときは必ずこの章を最初に読むこと。**  
**既存プロジェクトで新たに発見したノウハウは、汎用性があれば必ずここに追加する。**

### A. プロジェクト構成の鉄則

#### ブラウザツール（React + Express）
```
project-name/
├── SKILL.md / MEMORY.md / README.md
├── start.bat / stop.bat         # 必須：ワンクリック起動
├── .env.example / .gitignore
├── server/                      # Node.js + Express
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── index.ts
│       └── routes/
└── client/                      # React + Vite + Tailwind
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── index.html               # ★favicon必須
    ├── public/
    │   └── favicon.svg          # ★必須
    └── src/
        ├── App.tsx / main.tsx / index.css
        ├── components/
        └── types/
```

#### Pythonスクリプト/デーモン
```
project-name/
├── SKILL.md / MEMORY.md
├── requirements.txt
├── .env.example / .gitignore
├── src/
├── launcher.bat                 # VBSまたはBATで日本語パス回避
└── launcher.pyw                 # tkinter GUI（必要なら）
```

### B. ブラウザツールの必須要件（例外なし）

| # | 項目 | 必須内容 | 理由 |
|---|---|---|---|
| 1 | **favicon.svg** | `client/public/favicon.svg`＋`<link rel="icon">` | タブ識別・プロらしさ |
| 2 | **タイトル** | `<title>ツール名 - English Name</title>` | 日英併記で検索性UP |
| 3 | **ダークモード** | `<html class="dark">`＋Tailwind `darkMode:'class'` | 目の疲労軽減 |
| 4 | **アクセントカラー** | Tailwind設定で `accent` 定義（ツールごと識別色） | 複数ツール併用時の混乱防止 |
| 5 | **start.bat** | 依存自動インストール・ポート競合クリア・ヘルスチェック待機・ブラウザ自動起動 | 非エンジニアでも起動可能に |
| 6 | **stop.bat** | ポート指定でプロセスkill | 強制終了の安全策 |
| 7 | **proxy設定** | `vite.config.ts` で `/api` → `localhost:3001` | CORS回避 |
| 8 | **.gitignore** | `node_modules/` `dist/` `.env` `uploads/` `*.db` `.vite/` | 大容量・秘匿情報流出防止 |

**ファビコンデザインの指針：**
- SVG 64×64 ベクター（軽量・全解像度で綺麗）
- 背景色はダーク `#0f172a` 推奨
- ツールの機能を1目で伝える絵柄（例: drawing-checker=赤ペン×定規、plc-debugger=歯車×電気記号、email-assistant=封筒×AI）
- 最低2色使用（主役＋差し色）

### C. Python ⇄ Express ブリッジのパターン

**既存のPython CLIがあるなら、Python側をほぼ書き換えずにWeb化**できる。drawing-checkerで実証。

```python
# Python CLI に --json オプションを追加するだけ
parser.add_argument("--json", action="store_true")
parser.add_argument("--output-dir", type=Path, default=None)

# JSON出力はUTF-8バイトで直接stdoutへ（Windows cp932対策）
sys.stdout.buffer.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

# ログはstderrへ分離（超重要：ここをstdoutにするとJSON壊れる）
handler = logging.StreamHandler(sys.stderr)
```

```typescript
// Express 側（server/src/pythonRunner.ts）
const proc = spawn('python', ['-m', 'your_module', ...args], {
  env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONPATH: SRC_DIR },
  windowsHide: true,
});
// stdoutはJSONとしてパース、stderrはログとしてキャプチャ
```

### D. AI API の選定基準（実績ベース）

| 用途 | 推奨モデル | 理由 |
|---|---|---|
| テキスト処理・要約・単純タスク | **Gemini 2.5 Flash** | 安い・速い（email-assistantで実証） |
| 複雑な分析・コード生成 | **Claude Sonnet** | 精度最高（plc-debuggerで使用） |
| 画像＋テキスト（図面認識等） | **Gemini 2.5 Flash** | マルチモーダル対応・安い |
| ローカル実行（機密データ） | **Ollama + Llama3** | API代なし・ネット不要 |

**APIコスト抑制の鉄則：**
- デフォルトOFF、`--ai` フラグでオプトイン
- 失敗時フォールバック処理必須（AIは不正JSONを返すことがある）
- JSONパースエラー時は部分的にでも動作継続できる設計

### E. Windows環境の落とし穴（毎回引っかかる）

| 落とし穴 | 対策 |
|---|---|
| 日本語パスで起動失敗 | `.bat/.vbs` で英語パス経由起動 |
| multerの`originalname`がlatin1 | `Buffer.from(name, 'latin1').toString('utf-8')` |
| Python stdout の cp932 文字化け | `sys.stdout.buffer.write(data.encode('utf-8'))` |
| `console.log` / `print` の文字化け | `sys.stdout.reconfigure(encoding='utf-8')` |
| CRLF / LF の混在警告 | `git config core.autocrlf true` |
| タスクスケジューラからの起動 | 動作ディレクトリを絶対パスで指定 |
| 孤児プロセスが残る | Windows Job Object で親プロセスと連動（email-assistantで実証） |
| ポート競合（再起動時） | `netstat`＋`taskkill`でクリアしてから起動 |

### F. .gitignore の標準テンプレート

全プロジェクトで以下を基本形として採用：

```gitignore
# 秘匿情報（絶対にコミットしない）
.env
*.secret
*.pickle

# Python
__pycache__/
*.pyc
.venv/
venv/

# Node.js
node_modules/
dist/
.vite/

# ビルド成果物・大容量・機密
*/client/dist/
server/uploads/
server/results/
*.db
*.log

# 機密データ（学習結果・個人情報・顧客図面など）
config/learned_rules.json
*_checked.pdf
samples/*
!samples/.gitkeep

# OS / エディタ
.DS_Store
Thumbs.db
.vscode/
```

### G. start.bat / stop.bat の標準パターン

参考実装：`work-projects/drawing-checker/start.bat` または `work-projects/plc-debugger/start.bat`

`start.bat`の役割（順番通り）：
1. Node.js/Python の存在確認
2. `.env` の存在確認
3. `node_modules/` が無ければ `npm install` 自動実行
4. 既存プロセスの `taskkill`（ポート競合クリア）
5. バックエンド起動（バックグラウンド）
6. `/api/health` へヘルスチェック（最大30秒）
7. フロントエンド起動
8. ブラウザ自動オープン（`start "" "http://localhost:xxxx"`）

### H. ファイルアップロード（multer）の標準パターン

```typescript
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_DIR),
  filename: (_req, file, cb) => {
    // ★latin1 → UTF-8 デコード必須
    const original = Buffer.from(file.originalname, 'latin1').toString('utf-8');
    const id = crypto.randomBytes(6).toString('hex');
    const ext = path.extname(original);
    const base = path.basename(original, ext);
    // タイムスタンプ+ハッシュで一意化（同名上書き防止）
    cb(null, `${Date.now()}_${id}_${base}${ext}`);
  },
});
```

### I. データ移行のベストプラクティス

- エクスポート/インポート機能を **初版から組み込む**（media-transcriberで実証）
- SQLite を使う場合はDBファイル自体をバックアップ対象に
- 2台PC間の同期は GitHub + SessionStart/Stop フックで自動化

---

## ノウハウのエスカレーションルール

**誰かが学んだことは、全プロジェクトで共有される仕組み。**

```
プロジェクト固有の学び
  ↓
プロジェクトの SKILL.md / MEMORY.md に記録
  ↓
他プロジェクトでも使えそうか判定
  ↓ Yes
work-projects/MEMORY.md の「共通パターン」に昇格
  ↓
さらに汎用性が高い（全ツールに適用すべき）
  ↓ Yes
CLAUDE.md の「ツール・アプリ開発の標準パターン」に昇格
  ↓
以降、新プロジェクトは自動でこのノウハウを継承
```

### 判定基準
| 汎用度 | 置き場所 |
|---|---|
| 単一プロジェクトのみ | プロジェクト/MEMORY.md |
| 複数の類似プロジェクトに適用可 | work-projects/MEMORY.md 共通パターン |
| すべてのツール/アプリに適用すべき | CLAUDE.md 標準パターン |
| すべての業務（副業含む）に適用すべき | CLAUDE.md（両リポジトリに同期） |

### エスカレーションのタイミング
- 同じ失敗が2回以上起きた → 即座に禁止事項に追加＋上位へ昇格検討
- 特に効果的な手法を発見した → 成功パターンに追加＋上位へ昇格検討
- プロジェクト完了時の振り返りで「他でも使える」と判断した項目

---

## 進化の記録

### バージョン履歴
- v1.0：初期作成・全エージェント・全業務に適用開始

### 現在の強み
（運用開始後に記録）

### 現在の課題
（運用開始後に記録）

### 月次サマリー
（毎月末に記録）
