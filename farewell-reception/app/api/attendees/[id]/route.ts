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
    due?: number; // 「実際に受け取る金額」。指定時は調整額を逆算する
    fee?: number;
    support?: number;
    adjust?: number; // 調整額（＋多め／−割引）
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
  // fee/support は0以上、adjust は負も許可
  for (const key of ["fee", "support"] as const) {
    const v = body[key];
    if (typeof v === "number" && Number.isFinite(v) && v >= 0) {
      sets.push(`${key} = ?`);
      values.push(Math.round(v));
    }
  }
  if (typeof body.adjust === "number" && Number.isFinite(body.adjust)) {
    sets.push("adjust = ?");
    values.push(Math.round(body.adjust));
  }
  for (const key of ["dept", "name", "rank", "alcohol", "shuttle", "note"] as const) {
    const v = body[key];
    if (typeof v === "string") {
      if (key === "name" && v.trim() === "") return jsonError("氏名は必須です");
      sets.push(`${key} = ?`);
      values.push(key === "name" ? v.trim() : v);
    }
  }
  // due単独指定（受付タブの実徴収額）も有効な更新として扱う
  const dueOnly =
    typeof body.due === "number" && Number.isFinite(body.due) && body.due >= 0;
  if (sets.length === 0 && !dueOnly) return jsonError("nothing to update");

  const { env } = getCloudflareContext();
  if (sets.length > 0) {
    sets.push("updated_at = ?");
    values.push(new Date().toISOString());
    values.push(attendeeId);
    await env.DB.prepare(`UPDATE attendees SET ${sets.join(", ")} WHERE id = ?`)
      .bind(...values)
      .run();
  }

  // 金額に関わる変更があったら due を再計算（fee+support+adjust）。
  // 受付タブから「実際に受け取る金額（due）」が来た場合は、そこから adjust を逆算する。
  const cur = await env.DB.prepare(
    "SELECT fee, support, adjust, rank FROM attendees WHERE id = ?"
  )
    .bind(attendeeId)
    .first<{ fee: number; support: number; adjust: number; rank: string }>();

  if (cur) {
    const billable = cur.rank !== "招待" && cur.rank !== "欠席";
    if (typeof body.due === "number" && Number.isFinite(body.due) && body.due >= 0) {
      // 実徴収額 → 調整額を逆算
      const newAdjust = billable ? Math.round(body.due) - cur.fee - cur.support : 0;
      await env.DB.prepare(
        "UPDATE attendees SET adjust = ?, due = ? WHERE id = ?"
      )
        .bind(newAdjust, billable ? Math.round(body.due) : 0, attendeeId)
        .run();
    } else if (
      body.fee !== undefined ||
      body.support !== undefined ||
      body.adjust !== undefined
    ) {
      const due = billable ? Math.max(0, cur.fee + cur.support + cur.adjust) : 0;
      await env.DB.prepare("UPDATE attendees SET due = ? WHERE id = ?")
        .bind(due, attendeeId)
        .run();
    }
  }

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
