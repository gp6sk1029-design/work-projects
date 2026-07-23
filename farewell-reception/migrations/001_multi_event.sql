-- v1 → v2 マイグレーション（既存の attendees を残したまま複数イベント対応にする）
-- 個人情報は含まない（役職ベースの一括更新のみ）

-- 1) 新テーブル
CREATE TABLE IF NOT EXISTS events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT    NOT NULL,
  event_type  TEXT    NOT NULL DEFAULT '',
  event_date  TEXT    NOT NULL DEFAULT '',
  venue       TEXT    NOT NULL DEFAULT '',
  venue_addr  TEXT    NOT NULL DEFAULT '',
  venue_url   TEXT    NOT NULL DEFAULT '',
  organizer   TEXT    NOT NULL DEFAULT '',
  refund_flat INTEGER NOT NULL DEFAULT 0,
  is_active   INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT
);

CREATE TABLE IF NOT EXISTS ranks (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL,
  name     TEXT    NOT NULL,
  fee      INTEGER NOT NULL DEFAULT 0,
  support  INTEGER NOT NULL DEFAULT 0,
  grp      TEXT    NOT NULL DEFAULT 'flat',
  sort     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ranks_event ON ranks(event_id);

CREATE TABLE IF NOT EXISTS expenses (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id     INTEGER NOT NULL,
  kind         TEXT    NOT NULL DEFAULT 'fixed',
  name         TEXT    NOT NULL,
  budget_pp    INTEGER,
  budget_total INTEGER,
  actual       INTEGER,
  note         TEXT    NOT NULL DEFAULT '',
  sort         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_expenses_event ON expenses(event_id);

-- 2) attendees に event_id を追加（既存データはイベント1に紐付け）
ALTER TABLE attendees ADD COLUMN event_id INTEGER NOT NULL DEFAULT 1;
CREATE INDEX IF NOT EXISTS idx_attendees_event ON attendees(event_id);

-- 3) イベント1（宮元さん 送別会）を登録
INSERT INTO events (id, title, event_type, event_date, venue, venue_addr, venue_url, organizer, refund_flat, is_active, created_at)
VALUES (1, '宮元さん 送別会', '居酒屋', '2026-07-30', '和ごころ 福久',
        '〒679-4315 兵庫県たつの市新宮町井野原６９９−７００',
        'http://www.xn--28jb6o404iqtgn21d.jp/top/', '幸田', 0, 1, datetime('now'));

-- 4) 役職別会費テーブル（Excel設定シートの現行値）
INSERT INTO ranks (event_id, name, fee, support, grp, sort) VALUES
  (1, '社員', 6600, 0,     'flat', 1),
  (1, '技師', 6600, 0,     'flat', 2),
  (1, '主任', 6600, 0,     'flat', 3),
  (1, '係長', 6600, 0,     'flat', 4),
  (1, '課長', 6600, 3400,  'exec', 5),
  (1, '次長', 6600, 3400,  'exec', 6),
  (1, '部長', 6600, 13400, 'exec', 7),
  (1, '専務', 6600, 13400, 'exec', 8),
  (1, '常務', 6600, 13400, 'exec', 9),
  (1, '顧問', 6600, 13400, 'exec', 10),
  (1, '社長', 5000, 0,     'exec', 11);

-- 5) 費用（Excel収支管理シートの現行値）
INSERT INTO expenses (event_id, kind, name, budget_pp, budget_total, actual, sort) VALUES
  (1, 'fixed',    '記念品',             NULL, 19500, NULL, 1),
  (1, 'fixed',    '送迎バス代',         NULL, NULL,  NULL, 2),
  (1, 'variable', '食事代',             4400, NULL,  NULL, 1),
  (1, 'variable', 'お酒代・飲み放題代', 2200, NULL,  NULL, 2);

-- 6) 役職変更の反映（Excel側で専務・常務→顧問に変更済み）
UPDATE attendees SET rank = '顧問' WHERE rank IN ('専務', '常務');

-- 7) 参加者の金額をExcelの現行会費テーブルに同期（集金済みは無いため安全に一括更新）
--    招待・欠席は 0 のまま
UPDATE attendees SET fee = 6600, support = 0,     due = 6600  WHERE rank IN ('社員','技師','主任','係長');
UPDATE attendees SET fee = 6600, support = 3400,  due = 10000 WHERE rank IN ('課長','次長');
UPDATE attendees SET fee = 6600, support = 13400, due = 20000 WHERE rank IN ('部長','顧問');
UPDATE attendees SET fee = 5000, support = 0,     due = 5000  WHERE rank = '社長';
UPDATE attendees SET fee = 0,    support = 0,     due = 0     WHERE rank IN ('招待','欠席');
