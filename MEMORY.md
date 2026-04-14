# 本業プロジェクト MEMORY.md
# 学習・経験の蓄積

> タスク完了のたびに追記する。効果がなかったパターンは削除する。月1回整理する。

---

## ツール開発のノウハウ

### 共通パターン（全ツールに適用できる知見）

- **Webアプリ構成の鉄板**: client(React+Vite) + server(Express+SQLite) が最も開発速度が速い
- **起動の自動化**: start.bat でバックエンド起動確認後にブラウザ自動起動するパターンが使いやすい
- **AI API選定**: テキスト処理はGemini 2.5 Flash（安い・速い）、高度な分析はClaude API
- **日本語パス問題**: Windowsで日本語パスを含むスクリプトは英語パス経由のランチャーで回避する
- **大容量ファイル**: dist/、node_modules/、.db、動画ファイルは.gitignoreで必ず除外

### UI/フロントエンド
- 使用技術：React + TypeScript + Tailwind + Vite
- タブUIでマルチ機能を1画面に統合するパターンが好評（メール秘書で実証）
- ファイルアップロード → 処理状況表示 → 結果表示の3ステップUIが直感的

### バックエンド
- 使用技術：Node.js + Express + SQLite
- SQLiteは単一ファイルDBなのでデプロイが楽。ただし.gitignoreで除外すること
- エクスポート・インポート機能を付けておくとデータ移行が楽（media-transcriberで実装済み）

### Python スクリプト
- バックグラウンドデーモン: 無限ループ + sleep で定期実行（auto_draft.py方式）
- Windows Job Objectで孤児プロセス問題を解決（メール秘書で学んだ重要な知見）
- openpyxlのセル高さ自動計算: テキスト量に応じてcalc_h()関数で動的調整

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

### farewell-docs（送別会書類）
- 技術: Python + openpyxl / HTML
- Excel版とHTML版の両方を自動生成
- **学び**:
  - デスクトップパスに日本語が含まれる場合の対処が必要

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
