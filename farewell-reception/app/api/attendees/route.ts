import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import { SELECT_ATTENDEES, type Attendee } from "../../types";
import { activeEventId, jsonError } from "../lib";

export const dynamic = "force-dynamic";

// 参加者一覧（アクティブイベント）
export async function GET() {
  const { env } = getCloudflareContext();
  const eventId = await activeEventId();
  if (eventId === null) return Response.json({ attendees: [] });
  const { results } = await env.DB.prepare(SELECT_ATTENDEES)
    .bind(eventId)
    .all<Attendee>();
  return Response.json({ attendees: results ?? [] });
}

// 参加者を追加
export async function POST(req: NextRequest) {
  const body = (await req.json()) as Partial<Attendee>;
  if (!body.name || typeof body.name !== "string") {
    return jsonError("氏名は必須です");
  }
  const eventId = await activeEventId();
  if (eventId === null) return jsonError("アクティブなイベントがありません", 409);

  const fee = Math.max(0, Math.round(Number(body.fee) || 0));
  const support = Math.max(0, Math.round(Number(body.support) || 0));
  const adjust = Math.round(Number(body.adjust) || 0); // マイナス（割引）も許可
  // 徴収額は「会費＋ご支援金＋調整額」で自動計算。招待・欠席は0
  const isBillable = body.rank !== "招待" && body.rank !== "欠席";
  const due = isBillable ? Math.max(0, fee + support + adjust) : 0;

  const { env } = getCloudflareContext();
  const res = await env.DB.prepare(
    `INSERT INTO attendees (event_id, dept, name, rank, fee, support, adjust, due, alcohol, shuttle, note, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      eventId,
      String(body.dept ?? ""),
      body.name.trim(),
      String(body.rank ?? ""),
      fee,
      support,
      adjust,
      due,
      String(body.alcohol ?? ""),
      String(body.shuttle ?? ""),
      String(body.note ?? ""),
      new Date().toISOString()
    )
    .run();

  const row = await env.DB.prepare("SELECT * FROM attendees WHERE id = ?")
    .bind(res.meta.last_row_id)
    .first<Attendee>();
  return Response.json({ ok: true, attendee: row });
}
