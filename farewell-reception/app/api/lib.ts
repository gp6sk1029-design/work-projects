import { getCloudflareContext } from "@opennextjs/cloudflare";

// アクティブイベントのIDを返す（無ければ null）
export async function activeEventId(): Promise<number | null> {
  const { env } = getCloudflareContext();
  const row = await env.DB.prepare(
    "SELECT id FROM events WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
  ).first<{ id: number }>();
  return row?.id ?? null;
}

export function jsonError(message: string, status = 400) {
  return Response.json({ error: message }, { status });
}
