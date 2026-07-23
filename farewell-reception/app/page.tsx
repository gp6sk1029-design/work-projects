import { getCloudflareContext } from "@opennextjs/cloudflare";
import AppShell from "./AppShell";
import {
  SELECT_ATTENDEES,
  SELECT_EVENTS,
  SELECT_EXPENSES,
  SELECT_RANKS,
  type Attendee,
  type EventRow,
  type Expense,
  type Rank,
} from "./types";

export const dynamic = "force-dynamic";

export default async function Page() {
  const { env } = getCloudflareContext();

  const { results: events } = await env.DB.prepare(SELECT_EVENTS).all<EventRow>();
  const active = (events ?? []).find((e: EventRow) => e.is_active === 1) ?? null;

  let attendees: Attendee[] = [];
  let ranks: Rank[] = [];
  let expenses: Expense[] = [];
  if (active) {
    const [at, rk, ex] = await Promise.all([
      env.DB.prepare(SELECT_ATTENDEES).bind(active.id).all<Attendee>(),
      env.DB.prepare(SELECT_RANKS).bind(active.id).all<Rank>(),
      env.DB.prepare(SELECT_EXPENSES).bind(active.id).all<Expense>(),
    ]);
    attendees = at.results ?? [];
    ranks = rk.results ?? [];
    expenses = ex.results ?? [];
  }

  return (
    <AppShell
      initial={{ event: active, events: events ?? [], attendees, ranks, expenses }}
    />
  );
}
