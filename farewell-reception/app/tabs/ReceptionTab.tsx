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
      billableCount: billable.length, // 集金対象人数
      paidCount: billable.filter((a) => a.paid).length, // 集金済み人数
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

  // 実際に受け取る金額を入力（規定額との差は「調整額」として自動記録）
  async function editDue(a: Attendee) {
    const base = a.fee + a.support; // 規定額
    const input = window.prompt(
      `${a.dept ? a.dept + " " : ""}${a.name} さんから実際に受け取る金額（円）\n` +
        `規定額 ${yen(base)}円。多め・割引はこの欄で調整できます`,
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
    const prevAdjust = a.adjust;
    const newAdjust = value - base;
    setList(
      list.map((x) => (x.id === a.id ? { ...x, due: value, adjust: newAdjust } : x))
    );
    try {
      const res = await fetch(`/api/attendees/${a.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ due: value }), // サーバ側で調整額を逆算
      });
      if (!res.ok) throw new Error("update failed");
    } catch {
      setList(
        list.map((x) =>
          x.id === a.id ? { ...x, due: prevDue, adjust: prevAdjust } : x
        )
      );
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
          {/* 来場と未収を隣同士に（どちらも人数の進捗） */}
          <div className="rounded-lg bg-slate-800 py-2">
            <div className="text-[10px] text-slate-400">来場</div>
            <div className="text-lg font-bold tabular-nums">
              {stats.arrived}
              <span className="text-xs text-slate-400">/{stats.total}名</span>
            </div>
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
          <div className="rounded-lg bg-slate-800 py-2">
            <div className="text-[10px] text-slate-400">集金</div>
            <div className="text-lg font-bold tabular-nums text-emerald-400">
              {stats.paidCount}
              <span className="text-xs text-slate-400">/{stats.billableCount}名</span>
            </div>
            <div className="text-[10px] text-slate-500">
              {yen(stats.paidTotal)}/{yen(stats.dueTotal)}円
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
        {/* 操作ガイド＋列見出し */}
        <div className="mt-2 flex items-center gap-2">
          <p className="min-w-0 flex-1 text-[10px] text-slate-500">
            👉 各行の右にある2つのボタンをタップしてチェック
          </p>
          <span className="w-16 shrink-0 text-center text-[10px] font-bold text-emerald-400">
            来場
          </span>
          <span className="w-[4.5rem] shrink-0 text-center text-[10px] font-bold text-amber-400">
            集金
          </span>
          <span className="w-8 shrink-0" />
        </div>
      </header>

      {/* 参加者リスト */}
      <ul className="divide-y divide-slate-800">
        {shown.map((a) => {
          const needsPay = a.due > 0;
          // 4状態で色分け
          // 完了(来場＆集金)＝濃い緑 / 集金済のみ＝薄緑 / 来場したのに未集金＝警告(赤) / それ以外＝通常
          const done = a.arrived && (a.paid || !needsPay);
          const warn = a.arrived && needsPay && !a.paid; // 来場したのに未集金
          const paidOnly = a.paid && !a.arrived;
          const rowClass = done
            ? "bg-emerald-500/25"
            : warn
              ? "bg-rose-500/20 ring-1 ring-inset ring-rose-500/50"
              : paidOnly
                ? "bg-emerald-500/10"
                : "";
          return (
          <li
            key={a.id}
            className={`flex items-center gap-2 px-3 py-2 ${rowClass}`}
          >
            {/* 氏名・情報（表示のみ） */}
            <div className="min-w-0 flex-1">
              <span className="block truncate text-sm font-bold">
                {a.dept && (
                  <span className="mr-1 text-[10px] text-slate-400">{a.dept}</span>
                )}
                {a.name}
                {done && <span className="ml-1 text-[10px] text-emerald-400">✓完了</span>}
                {warn && (
                  <span className="ml-1 rounded bg-rose-500 px-1 text-[10px] font-bold text-white">
                    ⚠️未集金
                  </span>
                )}
              </span>
              <span className="block text-[10px] text-slate-400">
                {a.rank}
                {a.alcohol === "あり" && " ・🍺"}
                {a.shuttle === "あり" && " ・🚐"}
                {a.adjust !== 0 && (
                  <span className="ml-1 font-bold text-amber-400">
                    {a.adjust > 0 ? "＋" : "−"}
                    {yen(Math.abs(a.adjust))}
                  </span>
                )}
              </span>
            </div>

            {/* 来場チェック */}
            <button
              onClick={() => toggle(a.id, "arrived")}
              aria-pressed={a.arrived === 1}
              className={`flex h-14 w-16 shrink-0 flex-col items-center justify-center gap-1 rounded-lg border-2 transition-colors ${
                a.arrived
                  ? "border-emerald-500 bg-emerald-500 text-white"
                  : "border-slate-600 bg-slate-800/60 text-slate-400"
              }`}
            >
              <span
                className={`flex h-5 w-5 items-center justify-center rounded border-2 text-xs font-bold ${
                  a.arrived ? "border-white bg-white text-emerald-600" : "border-slate-500"
                }`}
              >
                {a.arrived ? "✓" : ""}
              </span>
              <span className="text-[10px] font-bold">来場</span>
            </button>

            {/* 集金チェック */}
            {a.due > 0 ? (
              <button
                onClick={() => toggle(a.id, "paid")}
                aria-pressed={a.paid === 1}
                className={`flex h-14 w-[4.5rem] shrink-0 flex-col items-center justify-center gap-0.5 rounded-lg border-2 transition-colors ${
                  a.paid
                    ? "border-emerald-500 bg-emerald-500 text-white"
                    : "border-amber-500/60 bg-amber-500/15 text-amber-300"
                }`}
              >
                {a.paid ? (
                  <>
                    <span className="flex h-5 w-5 items-center justify-center rounded border-2 border-white bg-white text-xs font-bold text-emerald-600">
                      ✓
                    </span>
                    <span className="text-[10px] font-bold">集金済</span>
                  </>
                ) : (
                  <>
                    <span className="text-[13px] font-bold tabular-nums leading-none">
                      {yen(a.due)}
                    </span>
                    <span className="flex items-center gap-0.5 text-[10px] font-bold">
                      <span className="flex h-3 w-3 items-center justify-center rounded-sm border border-amber-400" />
                      集金
                    </span>
                  </>
                )}
              </button>
            ) : (
              <span className="flex h-14 w-[4.5rem] shrink-0 items-center justify-center text-xs text-slate-500">
                {a.rank === "招待" ? "招待" : "―"}
              </span>
            )}

            {/* 料金変更 */}
            <button
              onClick={() => editDue(a)}
              aria-label={`${a.name}さんの金額を変更`}
              className="flex h-14 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-400 active:bg-slate-700"
            >
              ✏️
            </button>
          </li>
          );
        })}
        {shown.length === 0 && (
          <li className="px-4 py-10 text-center text-sm text-slate-500">
            該当する参加者がいません
          </li>
        )}
      </ul>

      <p className="px-4 py-6 text-center text-[10px] text-slate-600">
        行の色：<span className="text-emerald-400">濃い緑＝来場＆集金の完了</span>／
        <span className="text-emerald-300">薄い緑＝集金済み（未来場）</span>／
        <span className="text-rose-400">赤＝来場したのに未集金（要集金）</span>。
        「来場」「集金」ボタンはもう一度タップで取り消し。✏️で金額変更。自動保存されます。
      </p>
    </div>
  );
}
