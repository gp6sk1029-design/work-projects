import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import { activeEventId, jsonError } from "../lib";

export const dynamic = "force-dynamic";

// アクティブイベントのデータをリセット（次のイベント準備・使い回し用）
// targets: "attendance"（来場・集金を全クリア）/ "attendees"（参加者全削除）/ "expenses"（費用全削除）
export async function POST(req: NextRequest) {
  const body = (await req.json()) as { targets?: string[] };
  const targets = Array.isArray(body.targets) ? body.targets : [];
  if (targets.length === 0) return jsonError("リセット対象が指定されていません");

  const eventId = await activeEventId();
  if (eventId === null) return jsonError("アクティブなイベントがありません", 409);

  const { env } = getCloudflareContext();
  const done: string[] = [];

  if (targets.includes("attendance")) {
    // 参加者は残し、来場・集金のチェックだけ全クリア（前日の練習チェックを消す等）
    await env.DB.prepare(
      "UPDATE attendees SET arrived = 0, paid = 0, updated_at = ? WHERE event_id = ?"
    )
      .bind(new Date().toISOString(), eventId)
      .run();
    done.push("attendance");
  }
  if (targets.includes("attendees")) {
    await env.DB.prepare("DELETE FROM attendees WHERE event_id = ?")
      .bind(eventId)
      .run();
    done.push("attendees");
  }
  if (targets.includes("expenses")) {
    await env.DB.prepare("DELETE FROM expenses WHERE event_id = ?")
      .bind(eventId)
      .run();
    done.push("expenses");
  }

  return Response.json({ ok: true, done });
}
