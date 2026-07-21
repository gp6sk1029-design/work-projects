-- 歓送迎会 当日受付アプリ D1スキーマ
-- ※参加者の実データ（氏名・金額）はこのファイルに含めない（個人情報のためリポジトリ非コミット）

CREATE TABLE IF NOT EXISTS attendees (
  id         INTEGER PRIMARY KEY,
  dept       TEXT    NOT NULL DEFAULT '',   -- 部署（生技/設計/製技/営業 など）
  name       TEXT    NOT NULL,              -- 氏名
  rank       TEXT    NOT NULL DEFAULT '',   -- 役職（社員/技師/主任/係長/課長/次長/部長/専務/常務/顧問/社長/招待）
  fee        INTEGER NOT NULL DEFAULT 0,    -- 会費
  support    INTEGER NOT NULL DEFAULT 0,    -- ご支援金
  due        INTEGER NOT NULL DEFAULT 0,    -- 当日徴収額（会費＋ご支援金）
  alcohol    TEXT    NOT NULL DEFAULT '',   -- あり/なし
  shuttle    TEXT    NOT NULL DEFAULT '',   -- 送迎バス あり/なし
  note       TEXT    NOT NULL DEFAULT '',
  arrived    INTEGER NOT NULL DEFAULT 0,    -- 来場チェック 0/1
  paid       INTEGER NOT NULL DEFAULT 0,    -- 集金済みチェック 0/1
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_attendees_dept ON attendees(dept);
CREATE INDEX IF NOT EXISTS idx_attendees_paid ON attendees(paid);
