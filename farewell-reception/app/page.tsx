import { getCloudflareContext } from "@opennextjs/cloudflare";
import ReceptionClient from "./ReceptionClient";
import { SELECT_ATTENDEES, type Attendee } from "./types";

export const dynamic = "force-dynamic";

export default async function Page() {
  const { env } = getCloudflareContext();
  const { results } = await env.DB.prepare(SELECT_ATTENDEES).all<Attendee>();
  return <ReceptionClient initial={results ?? []} />;
}
