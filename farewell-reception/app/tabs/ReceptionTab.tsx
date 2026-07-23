"use client";

// 当日受付タブ（従来のReceptionClientと同機能。欠席者は表示しない）
import { useMemo, useState } from "react";
import type { Attendee, EventRow } from "../types";
import { yen } from "../calc";

export default function ReceptionTab({
  event,
  list,
  setList,
}: {
  event: EventRow | null;
  list: Attendee[];
  setList: (v: Attendee[]) => void;
}) {
  const [onlyUnpaid, setOnlyUnpaid] = useState(false);
  const [q, setQ] = useState("");

  const present = useMemo(() => list.filter((a) => a.rank !== "欠席"), [list]);

  const stats = useMemo(() => {
    const billable = present.filter((a) => a.due > 0);
    return {
      total: present.length,
      arrived: present.filter((a) => a.arrived).length,
      dueTotal: billable.reduce((s, a) => s + a.due, 0),
      paidTotal: billable.filter((a) => a.paid).reduce((s, a) => s + a.due, 0),
      unpaidCount: billable.filter((a) => !a.paid).length,
    };
  }, [present]);

  const shown = useMemo(() => {
    const key = q.trim();
    return present.filter((a) => {
      if (onlyUnpaid && (a.paid === 1 || a.due === 0)) return false;
      if (key && !`${a.dept}${a.name}${a.rank}`.includes(key)) return false;
      return true;
    });
  }, [present, onlyUnpaid, q]);

  // 楽観更新 → サーバー反映。失敗したら元に戻す
  async function toggle(id: number, field: "arrived" | "paid") {
    const target = list.find((a) => a.id === id);
    if (!target) return;
    const next = target[field] ? 0 : 1;
    setList(list.map((a) => (a.id === id ? { ...a, [field]: next } : a)));
    try {
      const res = await fetch(`/api/attendees/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: next === 1 }),
      });
      if (!res.ok) throw new Error("update failed");
    } catch {
      setList(list.map((a) => (a.id === id ? { ...a, [field]: target[field] } : a)));
      alert("更新に失敗しました。通信状況を確認してください。");
    }
  }

  // 料金（徴収額）を変更する
  async function editDue(a: Attendee) {
    const input = window.prompt(
      `${a.dept ? a.dept + " " : ""}${a.name} さんの徴収額（円）を入力`,
      String(a.due)
    );
    if (input === null) return;
    const value = Number(input.replace(/[^0-9]/g, ""));
    if (!Number.isFinite(value) || value < 0) {
      alert("金額は0以上の数字で入力してください。");
      return;
    }
    if (value === a.due) return;

    const prevDue = a.due;
    setList(list.map((x) => (x.id === a.id ? { ...x, due: value } : x)));
    try {
      const res = await fetch(`/api/attendees/${a.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ due: value }),
      });
      if (!res.ok) throw new Error("update failed");
    } catch {
      setList(list.map((x) => (x.id === a.id ? { ...x, due: prevDue } : x)));
      alert("金額の変更に失敗しました。通信状況を確認してください。");
    }
  }

  return (
    <div>
      {/* 集計バー（常時表示） */}
      <header className="sticky top-0 z-10 border-b border-slate-700 bg-slate-900/95 px-4 py-3 backdrop-blur">
        <h1 className="text-sm font-bold text-amber-400">
          {event ? `${event.title} 受付` : "受付"}
        </h1>
        <div className="mt-2 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-slate-800 py-2">
            <div className="text-[10px] text-slate-400">来場</div>
            <div className="text-lg font-bold tabular-nums">
              {stats.arrived}
              <span className="text-xs text-slate-400">/{stats.total}</span>
            </div>
          </div>
          <div className="rounded-lg bg-slate-800 py-2">
            <div className="text-[10px] text-slate-400">集金</div>
            <div className="text-lg font-bold tabular-nums text-emerald-400">
              {yen(stats.paidTotal)}
            </div>
            <div className="text-[10px] text-slate-500">/{yen(stats.dueTotal)}円</div>
          </div>
          <div className="rounded-lg bg-slate-800 py-2">
            <div className="text-[10px] text-slate-400">未収</div>
            <div
              className={`text-lg font-bold tabular-nums ${
                stats.unpaidCount ? "text-rose-400" : "text-emerald-400"
              }`}
            >
              {stats.unpaidCount}
              <span className="text-xs text-slate-400">名</span>
            </div>
          </div>
        </div>
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => setOnlyUnpaid(!onlyUnpaid)}
            className={`shrink-0 rounded-lg px-3 py-2 text-xs font-bold ${
              onlyUnpaid ? "bg-rose-500 text-white" : "bg-slate-800 text-slate-300"
            }`}
          >
            未収のみ
          </button>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="氏名・部署で検索"
            className="w-full rounded-lg bg-slate-800 px-3 py-2 text-sm outline-none placeholder:text-slate-500"
          />
        </div>
      </header>

      {/* 参加者リスト */}
      <ul className="divide-y divide-slate-800">
        {shown.map((a) => (
          <li
            key={a.id}
            className={`flex items-center gap-2 px-3 py-2 ${
              a.arrived ? "bg-slate-900/60" : ""
            }`}
          >
            {/* 来場トグル */}
            <button
              onClick={() => toggle(a.id, "arrived")}
              className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-3 text-left ${
                a.arrived ? "bg-emerald-500/10" : "bg-slate-800/40"
              }`}
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                  a.arrived
                    ? "bg-emerald-500 text-white"
                    : "border border-slate-600 text-slate-600"
                }`}
              >
                {a.arrived ? "✓" : ""}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-bold">
                  {a.dept && (
                    <span className="mr-1 text-[10px] text-slate-400">{a.dept}</span>
                  )}
                  {a.name}
                </span>
                <span className="block text-[10px] text-slate-400">
                  {a.rank}
                  {a.alcohol === "あり" && " ・🍺"}
                  {a.shuttle === "あり" && " ・🚐"}
                </span>
              </span>
            </button>

            {/* 集金トグル */}
            {a.due > 0 ? (
              <button
                onClick={() => toggle(a.id, "paid")}
                className={`w-24 shrink-0 rounded-lg py-3 text-center text-sm font-bold tabular-nums ${
                  a.paid
                    ? "bg-emerald-500 text-white"
                    : "bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/40"
                }`}
              >
                {a.paid ? "集金済" : `${yen(a.due)}円`}
              </button>
            ) : (
              <span className="w-24 shrink-0 text-center text-xs text-slate-500">
                {a.rank === "招待" ? "招待" : "―"}
              </span>
            )}

            {/* 料金変更 */}
            <button
              onClick={() => editDue(a)}
              aria-label={`${a.name}さんの金額を変更`}
              className="flex h-11 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-400 active:bg-slate-700"
            >
              ✏️
            </button>
          </li>
        ))}
        {shown.length === 0 && (
          <li className="px-4 py-10 text-center text-sm text-slate-500">
            該当する参加者がいません
          </li>
        )}
      </ul>

      <p className="px-4 py-6 text-center text-[10px] text-slate-600">
        氏名をタップで「来場」／金額をタップで「集金済」／✏️で金額を変更。変更は自動保存されます。
      </p>
    </div>
  );
}
