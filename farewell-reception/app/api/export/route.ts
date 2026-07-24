import { getCloudflareContext } from "@opennextjs/cloudflare";
import {
  SELECT_ATTENDEES,
  SELECT_EXPENSES,
  SELECT_RANKS,
  type Attendee,
  type EventRow,
  type Expense,
  type Rank,
} from "../../types";
import { activeEventId } from "../lib";

export const dynamic = "force-dynamic";

// エクスポートするデータの形（バージョン付きで将来の互換性を確保）
export type EventBackup = {
  format: "farewell-reception";
  version: 1;
  exportedAt: string;
  event: Omit<EventRow, "id" | "is_active">;
  ranks: Omit<Rank, "id" | "event_id">[];
  expenses: Omit<Expense, "id" | "event_id">[];
  attendees: Omit<Attendee, "id" | "event_id">[];
};

// アクティブイベントを1つのJSONにまとめて返す（保存・バックアップ用）
export async function GET() {
  const eventId = await activeEventId();
  if (eventId === null) {
    return Response.json({ error: "アクティブなイベントがありません" }, { status: 409 });
  }
  const { env } = getCloudflareContext();

  const event = await env.DB.prepare(
    "SELECT title, event_type, event_date, venue, venue_addr, venue_url, organizer, refund_flat FROM events WHERE id = ?"
  )
    .bind(eventId)
    .first<Omit<EventRow, "id" | "is_active">>();
  const ranks = await env.DB.prepare(SELECT_RANKS).bind(eventId).all<Rank>();
  const expenses = await env.DB.prepare(SELECT_EXPENSES).bind(eventId).all<Expense>();
  const attendees = await env.DB.prepare(SELECT_ATTENDEES).bind(eventId).all<Attendee>();

  const strip = <T extends Record<string, unknown>>(rows: T[], keys: string[]) =>
    rows.map((r) => {
      const o = { ...r };
      for (const k of keys) delete o[k];
      return o;
    });

  const backup: EventBackup = {
    format: "farewell-reception",
    version: 1,
    exportedAt: new Date().toISOString(),
    event: event!,
    ranks: strip(ranks.results ?? [], ["id", "event_id"]) as EventBackup["ranks"],
    expenses: strip(expenses.results ?? [], ["id", "event_id"]) as EventBackup["expenses"],
    attendees: strip(attendees.results ?? [], ["id", "event_id"]) as EventBackup["attendees"],
  };

  const filename = `farewell_${(event?.event_date || "event").replace(/[^0-9]/g, "")}_${(event?.title || "").replace(/[\s/\\?%*:|"<>]/g, "")}.json`;
  return new Response(JSON.stringify(backup, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": `attachment; filename="${encodeURIComponent(filename)}"`,
    },
  });
}
