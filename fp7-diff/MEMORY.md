# FP7 Diff MEMORY

## 開発履歴

### 2026-05-18 初版完成
- 担当: 生産技術主任補佐PDM
- 工数: 約3時間
- 状態: 動作確認済み（1号機・4号機の実データで検証）

### 学び（初版実装時）
- **.fpx 直接読込は不可**: バイナリ全体が圧縮/暗号化されており、UTF-16/Shift_JIS抽出も意味のある文字列ゼロ
  → エクスポート方式が唯一の現実解
- **FPWIN GR7 グローバルデバイス.txt は UTF-16 LE BOM付き**: Node.js では `buf.slice(2).toString('utf16le')` で読める
- **タブ区切り・4列形式**: `アドレス\tコメント\t\t` (後ろ2列は通常空)
- **カテゴリ判定は長い接頭辞から**: DT/LD/SD/SR/FL/WX/WY/WR を X/Y/R/L より先に判定しないと誤検出
- **multer日本語ファイル名**: `Buffer.from(file.originalname, 'latin1').toString('utf-8')` で復号（ブラウザは動く、curlは環境依存）
- **sql.js の型定義なし**: `declare module 'sql.js'` で対処（types.d.ts）

### 動作確認サンプル（1号機 vs 4号機）
- 1号機: 1219デバイス
- 4号機: 1245デバイス
- 変更: 37件（命名変更が主）
- 追加: 34件（DT3630等の「B<D 比較補正値」= 他列比較制御の新機能）
- 削除: 8件（R4010 測定方法切替SW等）
- 同一: 1174件

### ROI実績（初版）
- 開発工数: 3時間
- 想定削減: 月3時間 (年36時間) = 年間108,000円相当
- 回収期間: 約4週間

## 今後の改善候補
- PDF（ラダー図）の差分解析（Gemini Vision、次フェーズ）
- 履歴UIの追加
- 複数PB対応
- 印刷PDF→画像→OCR→テキストdiffのハイブリッドパス

## 既知の問題
- curlでの日本語ファイル名は文字化けする（ブラウザは正常）
- DTレジスタの内部数値型まで踏み込んでいない（コメントのみ比較）

## メンテナンスメモ
- GEMINI_API_KEY は plc-debugger と同じものを流用中
- ポート: backend 3002 / frontend 5174（plc-debugger と分離）
- DB: server/data/fp7-diff.db（plc-debugger と分離）
