import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import type { EventBackup } from "../export/route";
import { jsonError } from "../lib";

export const dynamic = "force-dynamic";

// JSONバックアップから新しいイベントを作成して読み込む（過去イベントの復元・振り返り用）
// 既存イベントは消さず、新規イベントとして追加してアクティブに切り替える
export async function POST(req: NextRequest) {
  let data: EventBackup;
  try {
    data = (await req.json()) as EventBackup;
  } catch {
    return jsonError("ファイルの読み込みに失敗しました（JSON形式ではありません）");
  }
  if (data?.format !== "farewell-reception" || !data.event) {
    return jsonError("このアプリのバックアップファイルではありません");
  }

  const { env } = getCloudflareContext();
  const now = new Date().toISOString();
  const e = data.event;

  // 新イベントを作成してアクティブに
  const res = await env.DB.prepare(
    `INSERT INTO events (title, event_type, event_date, venue, venue_addr, venue_url, organizer, refund_flat, is_active, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`
  )
    .bind(
      String(e.title ?? "読込イベント"),
      String(e.event_type ?? ""),
      String(e.event_date ?? ""),
      String(e.venue ?? ""),
      String(e.venue_addr ?? ""),
      String(e.venue_url ?? ""),
      String(e.organizer ?? ""),
      Math.max(0, Math.round(Number(e.refund_flat) || 0)),
      now
    )
    .run();
  const newId = res.meta.last_row_id as number;
  await env.DB.prepare("UPDATE events SET is_active = 0 WHERE id != ?").bind(newId).run();

  // 役職テーブル
  for (const r of data.ranks ?? []) {
    await env.DB.prepare(
      "INSERT INTO ranks (event_id, name, fee, support, grp, sort) VALUES (?, ?, ?, ?, ?, ?)"
    )
      .bind(
        newId,
        String(r.name ?? ""),
        Math.round(Number(r.fee) || 0),
        Math.round(Number(r.support) || 0),
        r.grp === "exec" ? "exec" : "flat",
        Math.round(Number(r.sort) || 0)
      )
      .run();
  }
  // 費用
  for (const x of data.expenses ?? []) {
    const n = (v: unknown) =>
      v === null || v === undefined ? null : Math.round(Number(v) || 0);
    await env.DB.prepare(
      "INSERT INTO expenses (event_id, kind, name, budget_pp, budget_total, actual, note, sort) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
      .bind(
        newId,
        x.kind === "variable" ? "variable" : "fixed",
        String(x.name ?? ""),
        n(x.budget_pp),
        n(x.budget_total),
        n(x.actual),
        String(x.note ?? ""),
        Math.round(Number(x.sort) || 0)
      )
      .run();
  }
  // 参加者（受付結果 arrived/paid も含めて復元）
  for (const a of data.attendees ?? []) {
    await env.DB.prepare(
      `INSERT INTO attendees (event_id, dept, name, rank, fee, support, adjust, due, alcohol, shuttle, note, arrived, paid, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
      .bind(
        newId,
        String(a.dept ?? ""),
        String(a.name ?? ""),
        String(a.rank ?? ""),
        Math.round(Number(a.fee) || 0),
        Math.round(Number(a.support) || 0),
        Math.round(Number(a.adjust) || 0),
        Math.round(Number(a.due) || 0),
        String(a.alcohol ?? ""),
        String(a.shuttle ?? ""),
        String(a.note ?? ""),
        a.arrived ? 1 : 0,
        a.paid ? 1 : 0,
        now
      )
      .run();
  }

  return Response.json({
    ok: true,
    eventId: newId,
    counts: {
      ranks: (data.ranks ?? []).length,
      expenses: (data.expenses ?? []).length,
      attendees: (data.attendees ?? []).length,
    },
  });
}
