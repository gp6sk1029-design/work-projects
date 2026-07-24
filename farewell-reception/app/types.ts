export type Attendee = {
  id: number;
  event_id: number;
  dept: string;
  name: string;
  rank: string; // 役職名 or 「招待」「欠席」
  fee: number;
  support: number;
  adjust: number; // 調整額（イレギュラー支払い。＋多め／−割引）
  due: number;
  alcohol: string;
  shuttle: string;
  note: string;
  arrived: number; // 0/1
  paid: number; // 0/1
};

export type EventRow = {
  id: number;
  title: string;
  event_type: string;
  event_date: string;
  venue: string;
  venue_addr: string;
  venue_url: string;
  organizer: string;
  refund_flat: number;
  is_active: number; // 0/1
};

export type Rank = {
  id: number;
  event_id: number;
  name: string;
  fee: number;
  support: number;
  grp: "flat" | "exec"; // flat=一般(一律返金) / exec=役職者(按分返金)
  sort: number;
};

export type Expense = {
  id: number;
  event_id: number;
  kind: "fixed" | "variable";
  name: string;
  budget_pp: number | null;
  budget_total: number | null;
  actual: number | null;
  note: string;
  sort: number;
};

// 特殊区分（ranksテーブル外）
export const SPECIAL_RANKS = ["招待", "欠席"] as const;

export const SELECT_ATTENDEES = `SELECT id, event_id, dept, name, rank, fee, support, adjust, due, alcohol, shuttle, note, arrived, paid
   FROM attendees WHERE event_id = ? ORDER BY id`;

export const SELECT_EVENTS = `SELECT id, title, event_type, event_date, venue, venue_addr, venue_url, organizer, refund_flat, is_active
   FROM events ORDER BY id DESC`;

export const SELECT_RANKS = `SELECT id, event_id, name, fee, support, grp, sort
   FROM ranks WHERE event_id = ? ORDER BY sort, id`;

export const SELECT_EXPENSES = `SELECT id, event_id, kind, name, budget_pp, budget_total, actual, note, sort
   FROM expenses WHERE event_id = ? ORDER BY kind, sort, id`;
