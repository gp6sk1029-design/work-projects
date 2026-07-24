import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import type { EventRow } from "../../../types";
import { jsonError } from "../../lib";

export const dynamic = "force-dynamic";

// イベント情報の更新（activate: true で運用中イベントを切り替え）
export async function PATCH(
  req: NextRequest,
  ctx: RouteContext<"/api/events/[id]">
) {
  const { id } = await ctx.params;
  const eventId = Number(id);
  if (!Number.isInteger(eventId)) return jsonError("invalid id");

  const body = (await req.json()) as Partial<EventRow> & { activate?: boolean };
  const { env } = getCloudflareContext();

  if (body.activate === true) {
    await env.DB.prepare("UPDATE events SET is_active = 0").run();
    await env.DB.prepare("UPDATE events SET is_active = 1 WHERE id = ?")
      .bind(eventId)
      .run();
  }

  const sets: string[] = [];
  const values: (number | string)[] = [];
  for (const key of [
    "title",
    "event_type",
    "event_date",
    "venue",
    "venue_addr",
    "venue_url",
    "organizer",
  ] as const) {
    const v = body[key];
    if (typeof v === "string") {
      if (key === "title" && v.trim() === "") return jsonError("イベント名は必須です");
      sets.push(`${key} = ?`);
      values.push(key === "title" ? v.trim() : v);
    }
  }
  if (
    typeof body.refund_flat === "number" &&
    Number.isFinite(body.refund_flat) &&
    body.refund_flat >= 0
  ) {
    sets.push("refund_flat = ?");
    values.push(Math.round(body.refund_flat));
  }
  if (sets.length > 0) {
    values.push(eventId);
    await env.DB.prepare(`UPDATE events SET ${sets.join(", ")} WHERE id = ?`)
      .bind(...values)
      .run();
  } else if (body.activate !== true) {
    return jsonError("nothing to update");
  }

  const row = await env.DB.prepare("SELECT * FROM events WHERE id = ?")
    .bind(eventId)
    .first<EventRow>();
  return Response.json({ ok: true, event: row });
}

// イベントを削除（参加者・役職・費用ごと）。最後の1件は削除不可。
// 運用中を消した場合は残りの最新イベントを自動で運用中にする
export async function DELETE(
  _req: NextRequest,
  ctx: RouteContext<"/api/events/[id]">
) {
  const { id } = await ctx.params;
  const eventId = Number(id);
  if (!Number.isInteger(eventId)) return jsonError("invalid id");

  const { env } = getCloudflareContext();
  const cnt = await env.DB.prepare("SELECT COUNT(*) AS c FROM events").first<{ c: number }>();
  if ((cnt?.c ?? 0) <= 1) {
    return jsonError("最後のイベントは削除できません", 409);
  }
  const target = await env.DB.prepare("SELECT is_active FROM events WHERE id = ?")
    .bind(eventId)
    .first<{ is_active: number }>();
  if (!target) return jsonError("not found", 404);

  // 紐づくデータごと削除
  await env.DB.prepare("DELETE FROM attendees WHERE event_id = ?").bind(eventId).run();
  await env.DB.prepare("DELETE FROM ranks WHERE event_id = ?").bind(eventId).run();
  await env.DB.prepare("DELETE FROM expenses WHERE event_id = ?").bind(eventId).run();
  await env.DB.prepare("DELETE FROM events WHERE id = ?").bind(eventId).run();

  // 運用中を消したら、残りの最新を運用中にする
  if (target.is_active === 1) {
    const next = await env.DB.prepare(
      "SELECT id FROM events ORDER BY id DESC LIMIT 1"
    ).first<{ id: number }>();
    if (next) {
      await env.DB.prepare("UPDATE events SET is_active = 1 WHERE id = ?")
        .bind(next.id)
        .run();
    }
  }
  return Response.json({ ok: true });
}
