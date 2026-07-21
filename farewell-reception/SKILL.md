# farewell-reception（歓送迎会 当日受付アプリ）

歓送迎会の**当日受付・集金管理**をスマホで行うWebアプリ。
参加者名簿を見ながら「来場」「集金済」をタップでチェックし、集金額・未収者をリアルタイム集計する。

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

## 画面

1画面完結。上部に集計バー（来場◯/33名・集金◯円/◯円・未収◯名）、下に参加者リスト。
- 氏名部分をタップ → 来場チェック
- 金額をタップ → 集金済チェック（楽観更新→API保存、失敗時ロールバック）
- 「未収のみ」ボタンで絞り込み、氏名・部署で検索可
- 招待者（徴収0円）は「招待」表示で集金対象外

## データ

`attendees` テーブル（schema.sql）。参加者データは会費収支管理Excelから生成する。

```bash
# Excel → SQL 変換（scratchのextract_members.pyを使用）
# → seed_attendees.sql が生成される（★個人情報：コミット禁止・.gitignore済み）

npm run db:init:local      # ローカルD1にスキーマ投入
npx wrangler d1 execute farewell-reception --local --file=seed_attendees.sql
npm run dev                # http://localhost:3000
```

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
