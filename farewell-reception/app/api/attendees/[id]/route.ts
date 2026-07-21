import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

// 来場／集金のチェックを更新
export async function PATCH(
  req: NextRequest,
  ctx: RouteContext<"/api/attendees/[id]">
) {
  const { id } = await ctx.params;
  const attendeeId = Number(id);
  if (!Number.isInteger(attendeeId)) {
    return Response.json({ error: "invalid id" }, { status: 400 });
  }

  const body = (await req.json()) as { arrived?: boolean; paid?: boolean };
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
  if (sets.length === 0) {
    return Response.json({ error: "nothing to update" }, { status: 400 });
  }

  sets.push("updated_at = ?");
  values.push(new Date().toISOString());
  values.push(attendeeId);

  const { env } = await getCloudflareContext({ async: true });
  await env.DB.prepare(`UPDATE attendees SET ${sets.join(", ")} WHERE id = ?`)
    .bind(...values)
    .run();

  const row = await env.DB.prepare(
    "SELECT id, arrived, paid FROM attendees WHERE id = ?"
  )
    .bind(attendeeId)
    .first();

  return Response.json({ ok: true, attendee: row });
}
