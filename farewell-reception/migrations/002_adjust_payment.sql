-- イレギュラー支払い対応：調整額カラムを追加
-- adjust: 規定額（fee+support）に対する増減。プラス=多く払う／マイナス=割引。個人ごとのイレギュラー
-- 個人情報なし（役職・氏名の一括更新のみ。中村さんの上乗せ額は業務指示ベースの固定値）

ALTER TABLE attendees ADD COLUMN adjust INTEGER NOT NULL DEFAULT 0;

-- 徴収額を「会費＋ご支援金＋調整額」に統一（既存は adjust=0 なので変化なし）
UPDATE attendees SET due = fee + support + adjust
  WHERE rank NOT IN ('招待', '欠席');

-- 中村さん（次長）を +10,000円のイレギュラー支払いに設定（計20,000円）
UPDATE attendees
  SET adjust = 10000, due = fee + support + 10000, note = TRIM(note || ' +10,000(多め徴収)'),
      updated_at = datetime('now')
  WHERE name = '中村' AND rank = '次長' AND event_id = 1;
