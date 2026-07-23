import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import { jsonError } from "../../lib";

export const dynamic = "force-dynamic";

// 参加者の更新（受付チェック・金額・プロフィールすべて）
export async function PATCH(
  req: NextRequest,
  ctx: RouteContext<"/api/attendees/[id]">
) {
  const { id } = await ctx.params;
  const attendeeId = Number(id);
  if (!Number.isInteger(attendeeId)) return jsonError("invalid id");

  const body = (await req.json()) as {
    arrived?: boolean;
    paid?: boolean;
    due?: number;
    fee?: number;
    support?: number;
    dept?: string;
    name?: string;
    rank?: string;
    alcohol?: string;
    shuttle?: string;
    note?: string;
  };
  const sets: string[] = [];
  const values: (number | string)[] = [];

  if (typeof body.arrived === "boolean") {
    sets.push("arrived = ?");
    values.push(body.arrived ? 1 : 0);
  }
  if (typeof body.paid === "boolean") {
    sets.push("paid = ?");
    values.push(body.paid ? 1 : 0);
  }
  for (const key of ["due", "fee", "support"] as const) {
    const v = body[key];
    if (typeof v === "number" && Number.isFinite(v) && v >= 0) {
      sets.push(`${key} = ?`);
      values.push(Math.round(v));
    }
  }
  for (const key of ["dept", "name", "rank", "alcohol", "shuttle", "note"] as const) {
    const v = body[key];
    if (typeof v === "string") {
      if (key === "name" && v.trim() === "") return jsonError("氏名は必須です");
      sets.push(`${key} = ?`);
      values.push(key === "name" ? v.trim() : v);
    }
  }
  if (sets.length === 0) return jsonError("nothing to update");

  sets.push("updated_at = ?");
  values.push(new Date().toISOString());
  values.push(attendeeId);

  const { env } = getCloudflareContext();
  await env.DB.prepare(`UPDATE attendees SET ${sets.join(", ")} WHERE id = ?`)
    .bind(...values)
    .run();

  const row = await env.DB.prepare("SELECT * FROM attendees WHERE id = ?")
    .bind(attendeeId)
    .first();
  return Response.json({ ok: true, attendee: row });
}

// 参加者を削除
export async function DELETE(
  _req: NextRequest,
  ctx: RouteContext<"/api/attendees/[id]">
) {
  const { id } = await ctx.params;
  const attendeeId = Number(id);
  if (!Number.isInteger(attendeeId)) return jsonError("invalid id");

  const { env } = getCloudflareContext();
  await env.DB.prepare("DELETE FROM attendees WHERE id = ?")
    .bind(attendeeId)
    .run();
  return Response.json({ ok: true });
}
