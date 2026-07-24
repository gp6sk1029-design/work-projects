-- 歓送迎会 受付・会費収支アプリ D1スキーマ v2（複数イベント対応）
-- ※参加者の実データ（氏名・金額）はこのファイルに含めない（個人情報のためリポジトリ非コミット）

-- イベント（歓送迎会1回＝1レコード。is_active=1 が現在運用中）
CREATE TABLE IF NOT EXISTS events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT    NOT NULL,              -- 例: 宮元さん 送別会
  event_type  TEXT    NOT NULL DEFAULT '',   -- 居酒屋/バーベキュー など
  event_date  TEXT    NOT NULL DEFAULT '',   -- YYYY-MM-DD
  venue       TEXT    NOT NULL DEFAULT '',   -- 店名
  venue_addr  TEXT    NOT NULL DEFAULT '',
  venue_url   TEXT    NOT NULL DEFAULT '',
  organizer   TEXT    NOT NULL DEFAULT '',   -- 幹事名
  refund_flat INTEGER NOT NULL DEFAULT 0,    -- 一般1人あたり返金の設定額（上限。余剰不足時は自動減額）
  is_active   INTEGER NOT NULL DEFAULT 0,    -- 1=現在運用中（常に1件のみ）
  created_at  TEXT
);

-- 役職別 会費テーブル（Excelの設定シート相当。イベントごとに持つ）
CREATE TABLE IF NOT EXISTS ranks (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  name     TEXT    NOT NULL,                 -- 役職名（社員/技師/…）
  fee      INTEGER NOT NULL DEFAULT 0,       -- 会費
  support  INTEGER NOT NULL DEFAULT 0,       -- ご支援金
  grp      TEXT    NOT NULL DEFAULT 'flat',  -- flat=一般(一律返金) / exec=役職者(按分返金)
  sort     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ranks_event ON ranks(event_id);

-- 費用（固定費・変動費。予算は「1人当たり」か「総額」のどちらか）
CREATE TABLE IF NOT EXISTS expenses (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id     INTEGER NOT NULL,
  kind         TEXT    NOT NULL DEFAULT 'fixed', -- fixed=固定費 / variable=変動費
  name         TEXT    NOT NULL,
  budget_pp    INTEGER,                          -- 1人当たり予算（×出席者数で予算合計）
  budget_total INTEGER,                          -- 総額予算（入力時はこちら優先）
  actual       INTEGER,                          -- 実績
  note         TEXT    NOT NULL DEFAULT '',
  sort         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_expenses_event ON expenses(event_id);

-- 参加者（rank には ranks.name のほか「招待」「欠席」も入る）
CREATE TABLE IF NOT EXISTS attendees (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id   INTEGER NOT NULL DEFAULT 1,
  dept       TEXT    NOT NULL DEFAULT '',   -- 部署（生技/設計/製技/営業 など）
  name       TEXT    NOT NULL,              -- 氏名
  rank       TEXT    NOT NULL DEFAULT '',   -- 役職 or 招待/欠席
  fee        INTEGER NOT NULL DEFAULT 0,    -- 会費
  support    INTEGER NOT NULL DEFAULT 0,    -- ご支援金
  adjust     INTEGER NOT NULL DEFAULT 0,    -- 調整額（イレギュラー支払い。＋多め／−割引）
  due        INTEGER NOT NULL DEFAULT 0,    -- 当日徴収額（会費＋ご支援金＋調整額）
  alcohol    TEXT    NOT NULL DEFAULT '',   -- あり/なし
  shuttle    TEXT    NOT NULL DEFAULT '',   -- 送迎バス あり/なし
  note       TEXT    NOT NULL DEFAULT '',
  arrived    INTEGER NOT NULL DEFAULT 0,    -- 来場チェック 0/1
  paid       INTEGER NOT NULL DEFAULT 0,    -- 集金済みチェック 0/1
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_attendees_event ON attendees(event_id);
CREATE INDEX IF NOT EXISTS idx_attendees_dept ON attendees(dept);
CREATE INDEX IF NOT EXISTS idx_attendees_paid ON attendees(paid);
