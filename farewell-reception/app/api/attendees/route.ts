import { getCloudflareContext } from "@opennextjs/cloudflare";
import { SELECT_ATTENDEES, type Attendee } from "../../types";

export const dynamic = "force-dynamic";

// 参加者一覧（受付画面の再読込用）
export async function GET() {
  const { env } = await getCloudflareContext({ async: true });
  const { results } = await env.DB.prepare(SELECT_ATTENDEES).all<Attendee>();
  return Response.json({ attendees: results ?? [] });
}
