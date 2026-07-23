# farewell-reception（歓送迎会 受付・会費収支アプリ）

歓送迎会の**当日受付・集金管理＋会費収支管理**をスマホで行うWebアプリ。
会費収支管理Excelと同等の機能を実装済みで、**複数イベント対応＝今後の歓送迎会でも使い回せる**。

## 機能（5タブ構成）

| タブ | 機能 |
|---|---|
| ✅受付 | 来場チェック・集金チェック・✏️金額変更・未収絞り込み・検索・集計バー（従来機能） |
| 👥参加者 | 追加・編集・削除。役職を選ぶと会費・ご支援金が自動設定。招待/欠席の区分あり |
| 💰費用 | 固定費・変動費の管理。予算は「1人当たり×出席者数」か「総額」の2方式。実績入力で差額管理 |
| 📊収支 | 収支サマリー（予算/実績2本立て）・余剰金・返金配分（一般=一律・役職者=按分）・役職別実質負担 |
| ⚙️設定 | イベント情報・役職別会費テーブル・返金設定・**イベント切替/新規作成**（会費テーブルは引き継ぎ） |

## ROI試算

| 項目 | 内容 |
|---|---|
| 削減対象 | 当日の受付・集金消し込み（紙名簿）＋集金額の手計算 |
| 削減効果 | 1回あたり約20分 × 年3回＝**約60分/年**＋未収の取りこぼし防止（1件5,000〜25,000円） |
| 開発コスト | 約6時間 |
| 回収 | 自部署のみで3〜4年／**他部署へ横展開すれば1年以内** |

## 構成（社内ルール準拠）

- フレームワーク：**Next.js 16**（App Router）
- ホスティング：**Cloudflare Workers**（@opennextjs/cloudflare）
- DB：**Cloudflare D1**
- 認証：**Cloudflare Access**（幹事のメールアドレスのみ許可）
- `wrangler.jsonc` に `"preview_urls": false`（Accessバイパス防止・**必須**）

⚠️ **このNext.jsは通常版と異なる**（`AGENTS.md` 参照）。コードを書く前に必ず
`node_modules/next/dist/docs/` の該当ガイドを読むこと。
例：Route Handlerの型は `RouteContext<"/api/attendees/[id]">`、`params` は **Promise**。

## データ（スキーマv2・複数イベント対応）

`events`（イベント）/ `ranks`（役職別会費テーブル）/ `expenses`（費用）/ `attendees`（参加者）の4テーブル。
`events.is_active=1` が運用中イベントで、全タブはアクティブイベントのデータを表示する。

- 既存v1からの移行は `migrations/001_multi_event.sql`（個人情報なし・役職ベースの一括更新のみ）
- 参加者の追加は**アプリの参加者タブから直接**行える（Excelからの一括取込は tools_extract_members.py）

```bash
npm run db:init:local      # ローカルD1にスキーマ投入（新規のみ）
npx wrangler d1 execute farewell-reception --local --file=migrations/001_multi_event.sql  # v1→v2移行
npm run dev                # http://localhost:3000
```

## 次回イベントでの使い方（使い回し手順）

1. ⚙️設定タブ →「＋新しいイベント」→ イベント名を入力（役職別会費テーブルは自動コピー）
2. ⚙️設定でイベント情報（開催日・会場・幹事）と会費テーブルの金額を調整
3. 👥参加者タブで参加者を登録（役職を選ぶと金額自動）
4. 💰費用タブで予算を入力 → 📊収支で見込み確認
5. 当日は✅受付タブで消し込み → 後日、費用実績を入れて返金額を確定
※過去イベントのデータは消えない。設定タブのイベント一覧からいつでも切替可

## デプロイ手順

```bash
npx wrangler login                                  # 初回のみ（対話式・人が実行）
npx wrangler d1 create farewell-reception           # database_id を wrangler.jsonc に記入
npm run db:init:remote                              # 本番D1にスキーマ
npx wrangler d1 execute farewell-reception --remote --file=seed_attendees.sql
npm run deploy
```

デプロイ後、**Cloudflareダッシュボードで Access アプリケーションを作成**し、
幹事のメールアドレスのみ許可する（これをしないと社外から見えてしまう）。

## 禁止事項

- 参加者データ（氏名・金額）を**リポジトリにコミットしない**（.gitignore済み）
- `preview_urls: false` を外さない
- 認証を自前実装しない（Cloudflare Accessに任せる）

## 自己改善ループ（CLAUDE.mdに準拠）

このエージェントはCLAUDE.mdの方針に従い、タスク完了のたびに振り返りレポートを出力し、
SKILL.mdとMEMORY.mdを更新し続ける。ROI評価を毎回行い、費用対効果を最大化する。

## 今後の拡張候補

- 出欠回答フォーム（参加者がスマホで回答→メール集計を不要に。効果大）
- 会費収支Excelへの実績書き戻し（集金結果→収支管理シート）
- 複数イベント対応（現在は1イベント固定）
