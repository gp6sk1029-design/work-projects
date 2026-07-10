# FP7 Diff スキル

Panasonic FP7 (FPWIN GR7) プログラム比較・分析ツール。
グローバルデバイスエクスポート（.txt）を2つ取り込み、変数・コメント差分とAI解説を出力する。

## 自己改善ループ（CLAUDE.mdに準拠）
このツールは CLAUDE.md の方針に従い、タスク完了のたびに振り返りレポートを出力し、
SKILL.md と MEMORY.md を更新し続ける。ROI評価を毎回行い、費用対効果を最大化する。

## ROI試算
- 月削減時間: 3時間（手動比較60分→ツール3分 × 月3-5回）
- 月価値: 約9,000円相当（時給3,000円）
- 開発コスト: 約4時間
- 回収期間: 約4週間

## アーキテクチャ
```
client (React+Vite+Tailwind, port 5174)
  └─ FileUploadArea / DiffSummary / DiffViewer / AiAnalysisPanel
       ↓ /api/compare
server (Express+sql.js, port 3002)
  ├─ globalDeviceParser.ts  (UTF-16 LE BOM対応・カテゴリ判定)
  ├─ diffCalculator.ts      (4状態分類: changed/added/removed/same)
  ├─ aiSummarizer.ts        (Gemini 2.5 Flash で業務的解説生成)
  └─ pdfAnalyzer.ts         (PDFラダー図解析・次フェーズ)
```

## 対応するデバイスカテゴリ
X物理入力 / Y物理出力 / R内部リレー / L リンクリレー / T タイマー / C カウンタ /
DT データレジスタ / LD リンクD / SD システムD / SR システムR / FL ファイルレジスタ /
P ポインタ / WX/WY/WR ワード型

## 入力ファイル形式
- FPWIN GR7「グローバルデバイス」エクスポート (.txt)
- UTF-16 LE BOM付き、タブ区切り
- フォーマット: `アドレス\tコメント\t属性1\t属性2`

## 起動方法
- デスクトップ「FP7 Diff」ショートカット → ワンクリック
- または `start.bat` をダブルクリック
- 既に起動中ならブラウザだけ開く（open-fp7-diff.bat 経由）

## 設計の鉄則
1. **差分の意味を伝える**: 件数だけでなく、横展開・標準化・改造履歴の観点で解説
2. **API代を最小化**: AI解説はサンプリング50件×3カテゴリのみ、デフォルトオプトイン
3. **CSV出力対応**: 詳細分析は表計算ソフトで（UTF-8 BOM付きCSV）
4. **大量行に強い**: 上位1000件のみ表示、フィルタ＋検索で絞り込み

## 既知の制約・今後の対応
- [ ] PDF（ラダー図印刷）の差分解析は次フェーズ（Gemini Vision）
- [ ] 履歴の閲覧UI未実装
- [ ] 複数PB（プログラムブロック）対応未着手
