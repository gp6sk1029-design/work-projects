import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import { SELECT_EVENTS, type EventRow } from "../../types";
import { jsonError } from "../lib";

export const dynamic = "force-dynamic";

// イベント一覧
export async function GET() {
  const { env } = getCloudflareContext();
  const { results } = await env.DB.prepare(SELECT_EVENTS).all<EventRow>();
  return Response.json({ events: results ?? [] });
}

// イベントを新規作成（アクティブに切り替え、既定の役職テーブルをコピー）
export async function POST(req: NextRequest) {
  const body = (await req.json()) as Partial<EventRow> & {
    copyRanksFrom?: number; // 役職テーブルをコピーする元イベントID（省略時は現アクティブ）
  };
  if (!body.title || typeof body.title !== "string") {
    return jsonError("イベント名は必須です");
  }

  const { env } = getCloudflareContext();
  const prevActive = await env.DB.prepare(
    "SELECT id FROM events WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
  ).first<{ id: number }>();

  const res = await env.DB.prepare(
    `INSERT INTO events (title, event_type, event_date, venue, venue_addr, venue_url, organizer, refund_flat, is_active, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`
  )
    .bind(
      body.title.trim(),
      String(body.event_type ?? ""),
      String(body.event_date ?? ""),
      String(body.venue ?? ""),
      String(body.venue_addr ?? ""),
      String(body.venue_url ?? ""),
      String(body.organizer ?? ""),
      Math.max(0, Math.round(Number(body.refund_flat) || 0)),
      new Date().toISOString()
    )
    .run();
  const newId = res.meta.last_row_id as number;

  // 新イベントをアクティブに（旧アクティブは解除）
  await env.DB.prepare("UPDATE events SET is_active = 0 WHERE id != ?")
    .bind(newId)
    .run();

  // 役職テーブルを前イベントからコピー（次回も同じ会費体系でスタートできる）
  const copyFrom = body.copyRanksFrom ?? prevActive?.id;
  if (copyFrom) {
    await env.DB.prepare(
      `INSERT INTO ranks (event_id, name, fee, support, grp, sort)
       SELECT ?, name, fee, support, grp, sort FROM ranks WHERE event_id = ?`
    )
      .bind(newId, copyFrom)
      .run();
  }

  const row = await env.DB.prepare("SELECT * FROM events WHERE id = ?")
    .bind(newId)
    .first<EventRow>();
  return Response.json({ ok: true, event: row });
}
