import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import { SELECT_RANKS, type Rank } from "../../types";
import { activeEventId, jsonError } from "../lib";

export const dynamic = "force-dynamic";

// 役職別会費テーブル（アクティブイベント）
export async function GET() {
  const { env } = getCloudflareContext();
  const eventId = await activeEventId();
  if (eventId === null) return Response.json({ ranks: [] });
  const { results } = await env.DB.prepare(SELECT_RANKS)
    .bind(eventId)
    .all<Rank>();
  return Response.json({ ranks: results ?? [] });
}

// 役職を追加
export async function POST(req: NextRequest) {
  const body = (await req.json()) as Partial<Rank>;
  if (!body.name || typeof body.name !== "string") {
    return jsonError("役職名は必須です");
  }
  const eventId = await activeEventId();
  if (eventId === null) return jsonError("アクティブなイベントがありません", 409);

  const { env } = getCloudflareContext();
  const max = await env.DB.prepare(
    "SELECT COALESCE(MAX(sort), 0) AS m FROM ranks WHERE event_id = ?"
  )
    .bind(eventId)
    .first<{ m: number }>();
  const res = await env.DB.prepare(
    "INSERT INTO ranks (event_id, name, fee, support, grp, sort) VALUES (?, ?, ?, ?, ?, ?)"
  )
    .bind(
      eventId,
      body.name.trim(),
      Math.max(0, Math.round(Number(body.fee) || 0)),
      Math.max(0, Math.round(Number(body.support) || 0)),
      body.grp === "exec" ? "exec" : "flat",
      (max?.m ?? 0) + 1
    )
    .run();
  const row = await env.DB.prepare("SELECT * FROM ranks WHERE id = ?")
    .bind(res.meta.last_row_id)
    .first<Rank>();
  return Response.json({ ok: true, rank: row });
}
