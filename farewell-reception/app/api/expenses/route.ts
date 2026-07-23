import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import { SELECT_EXPENSES, type Expense } from "../../types";
import { activeEventId, jsonError } from "../lib";

export const dynamic = "force-dynamic";

// 費用一覧（アクティブイベント）
export async function GET() {
  const { env } = getCloudflareContext();
  const eventId = await activeEventId();
  if (eventId === null) return Response.json({ expenses: [] });
  const { results } = await env.DB.prepare(SELECT_EXPENSES)
    .bind(eventId)
    .all<Expense>();
  return Response.json({ expenses: results ?? [] });
}

// 費用項目を追加
export async function POST(req: NextRequest) {
  const body = (await req.json()) as Partial<Expense>;
  if (!body.name || typeof body.name !== "string") {
    return jsonError("項目名は必須です");
  }
  const kind = body.kind === "variable" ? "variable" : "fixed";
  const eventId = await activeEventId();
  if (eventId === null) return jsonError("アクティブなイベントがありません", 409);

  const toIntOrNull = (v: unknown) =>
    typeof v === "number" && Number.isFinite(v) && v >= 0 ? Math.round(v) : null;

  const { env } = getCloudflareContext();
  const max = await env.DB.prepare(
    "SELECT COALESCE(MAX(sort), 0) AS m FROM expenses WHERE event_id = ? AND kind = ?"
  )
    .bind(eventId, kind)
    .first<{ m: number }>();
  const res = await env.DB.prepare(
    `INSERT INTO expenses (event_id, kind, name, budget_pp, budget_total, actual, note, sort)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      eventId,
      kind,
      body.name.trim(),
      toIntOrNull(body.budget_pp),
      toIntOrNull(body.budget_total),
      toIntOrNull(body.actual),
      String(body.note ?? ""),
      (max?.m ?? 0) + 1
    )
    .run();
  const row = await env.DB.prepare("SELECT * FROM expenses WHERE id = ?")
    .bind(res.meta.last_row_id)
    .first<Expense>();
  return Response.json({ ok: true, expense: row });
}
