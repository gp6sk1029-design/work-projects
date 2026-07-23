"use client";

import { useState } from "react";
import type { Attendee, EventRow, Expense, Rank } from "./types";
import ReceptionTab from "./tabs/ReceptionTab";
import AttendeesTab from "./tabs/AttendeesTab";
import ExpensesTab from "./tabs/ExpensesTab";
import SummaryTab from "./tabs/SummaryTab";
import SettingsTab from "./tabs/SettingsTab";

export type Store = {
  event: EventRow | null;
  events: EventRow[];
  attendees: Attendee[];
  ranks: Rank[];
  expenses: Expense[];
};

const TABS = [
  { key: "reception", label: "受付", icon: "✅" },
  { key: "attendees", label: "参加者", icon: "👥" },
  { key: "expenses", label: "費用", icon: "💰" },
  { key: "summary", label: "収支", icon: "📊" },
  { key: "settings", label: "設定", icon: "⚙️" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

export default function AppShell({ initial }: { initial: Store }) {
  const [store, setStore] = useState<Store>(initial);
  const [tab, setTab] = useState<TabKey>("reception");

  // アクティブイベント切替・作成後に全データを読み直す
  async function reloadAll() {
    const [ev, at, rk, ex] = await Promise.all([
      fetch("/api/events").then((r) => r.json() as Promise<{ events: EventRow[] }>),
      fetch("/api/attendees").then((r) => r.json() as Promise<{ attendees: Attendee[] }>),
      fetch("/api/ranks").then((r) => r.json() as Promise<{ ranks: Rank[] }>),
      fetch("/api/expenses").then((r) => r.json() as Promise<{ expenses: Expense[] }>),
    ]);
    setStore({
      events: ev.events,
      event: ev.events.find((e) => e.is_active === 1) ?? null,
      attendees: at.attendees,
      ranks: rk.ranks,
      expenses: ex.expenses,
    });
  }

  const set = <K extends keyof Store>(key: K, value: Store[K]) =>
    setStore((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="min-h-dvh bg-slate-950 pb-20 text-slate-100">
      {tab === "reception" && (
        <ReceptionTab
          event={store.event}
          list={store.attendees}
          setList={(v) => set("attendees", v)}
        />
      )}
      {tab === "attendees" && (
        <AttendeesTab
          list={store.attendees}
          ranks={store.ranks}
          setList={(v) => set("attendees", v)}
        />
      )}
      {tab === "expenses" && (
        <ExpensesTab
          expenses={store.expenses}
          attendees={store.attendees}
          setExpenses={(v) => set("expenses", v)}
        />
      )}
      {tab === "summary" && (
        <SummaryTab
          event={store.event}
          attendees={store.attendees}
          ranks={store.ranks}
          expenses={store.expenses}
        />
      )}
      {tab === "settings" && (
        <SettingsTab
          store={store}
          setEvent={(v) => set("event", v)}
          setRanks={(v) => set("ranks", v)}
          setAttendees={(v) => set("attendees", v)}
          reloadAll={reloadAll}
        />
      )}

      {/* 下部タブバー */}
      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-700 bg-slate-900/95 backdrop-blur">
        <div className="mx-auto flex max-w-xl">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-1 py-2 text-center text-[10px] ${
                tab === t.key ? "text-amber-400" : "text-slate-500"
              }`}
            >
              <span className="block text-lg leading-6">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}
