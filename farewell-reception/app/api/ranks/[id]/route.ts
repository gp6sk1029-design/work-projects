import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import type { Rank } from "../../../types";
import { jsonError } from "../../lib";

export const dynamic = "force-dynamic";

// 役職の会費・ご支援金・グループを更新
export async function PATCH(
  req: NextRequest,
  ctx: RouteContext<"/api/ranks/[id]">
) {
  const { id } = await ctx.params;
  const rankId = Number(id);
  if (!Number.isInteger(rankId)) return jsonError("invalid id");

  const body = (await req.json()) as Partial<Rank> & {
    applyToAttendees?: boolean; // 参加者の金額にも反映するか
  };
  const sets: string[] = [];
  const values: (number | string)[] = [];

  if (typeof body.name === "string" && body.name.trim() !== "") {
    sets.push("name = ?");
    values.push(body.name.trim());
  }
  for (const key of ["fee", "support"] as const) {
    const v = body[key];
    if (typeof v === "number" && Number.isFinite(v) && v >= 0) {
      sets.push(`${key} = ?`);
      values.push(Math.round(v));
    }
  }
  if (body.grp === "flat" || body.grp === "exec") {
    sets.push("grp = ?");
    values.push(body.grp);
  }
  if (sets.length === 0) return jsonError("nothing to update");

  values.push(rankId);
  const { env } = getCloudflareContext();
  const before = await env.DB.prepare("SELECT * FROM ranks WHERE id = ?")
    .bind(rankId)
    .first<Rank>();
  if (!before) return jsonError("not found", 404);

  await env.DB.prepare(`UPDATE ranks SET ${sets.join(", ")} WHERE id = ?`)
    .bind(...values)
    .run();
  const after = await env.DB.prepare("SELECT * FROM ranks WHERE id = ?")
    .bind(rankId)
    .first<Rank>();

  // 会費変更を同役職の参加者にも反映（既定ON）
  if (after && body.applyToAttendees !== false) {
    await env.DB.prepare(
      `UPDATE attendees SET fee = ?, support = ?, due = ?, updated_at = ?
       WHERE event_id = ? AND rank = ?`
    )
      .bind(
        after.fee,
        after.support,
        after.fee + after.support,
        new Date().toISOString(),
        after.event_id,
        after.name
      )
      .run();
  }

  return Response.json({ ok: true, rank: after });
}

// 役職を削除（その役職の参加者がいる場合は拒否）
export async function DELETE(
  _req: NextRequest,
  ctx: RouteContext<"/api/ranks/[id]">
) {
  const { id } = await ctx.params;
  const rankId = Number(id);
  if (!Number.isInteger(rankId)) return jsonError("invalid id");

  const { env } = getCloudflareContext();
  const rank = await env.DB.prepare("SELECT * FROM ranks WHERE id = ?")
    .bind(rankId)
    .first<Rank>();
  if (!rank) return jsonError("not found", 404);

  const used = await env.DB.prepare(
    "SELECT COUNT(*) AS c FROM attendees WHERE event_id = ? AND rank = ?"
  )
    .bind(rank.event_id, rank.name)
    .first<{ c: number }>();
  if ((used?.c ?? 0) > 0) {
    return jsonError(`この役職の参加者が${used!.c}名いるため削除できません`, 409);
  }

  await env.DB.prepare("DELETE FROM ranks WHERE id = ?").bind(rankId).run();
  return Response.json({ ok: true });
}
