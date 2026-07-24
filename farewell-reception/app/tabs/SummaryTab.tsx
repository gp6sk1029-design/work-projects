"use client";

// 収支サマリータブ：Excelの収支管理シート下部と同等（予算／実績の2本立て＋返金配分）
import { useMemo } from "react";
import type { Attendee, EventRow, Expense, Rank } from "../types";
import { computeSummary, rankRefund, yen } from "../calc";

export default function SummaryTab({
  event,
  attendees,
  ranks,
  expenses,
}: {
  event: EventRow | null;
  attendees: Attendee[];
  ranks: Rank[];
  expenses: Expense[];
}) {
  const s = useMemo(
    () => computeSummary(attendees, ranks, expenses, event),
    [attendees, ranks, expenses, event]
  );

  const Row = ({
    label,
    budget,
    actual,
    strong,
    color,
  }: {
    label: string;
    budget: string;
    actual: string;
    strong?: boolean;
    color?: string;
  }) => (
    <div
      className={`grid grid-cols-[1fr_5.5rem_5.5rem] items-center gap-2 px-4 py-2 ${
        strong ? "bg-slate-900 font-bold" : ""
      }`}
    >
      <span className="text-xs text-slate-300">{label}</span>
      <span className={`text-right text-sm tabular-nums ${color ?? ""}`}>{budget}</span>
      <span className={`text-right text-sm tabular-nums ${color ?? ""}`}>{actual}</span>
    </div>
  );

  // 実績が入っていれば実績ベース、なければ予算ベースで表示
  const useActual = s.hasActual;
  const flatRefund = useActual ? s.refundFlatActual ?? 0 : s.refundFlatBudget;
  const leftover = useActual
    ? s.execLeftoverActual ?? 0
    : s.execLeftoverBudget;

  return (
    <div>
      <header className="sticky top-0 z-10 border-b border-slate-700 bg-slate-900/95 px-4 py-3 backdrop-blur">
        <h1 className="text-sm font-bold text-amber-400">収支サマリー</h1>
        <p className="mt-0.5 text-[10px] text-slate-500">
          会費負担{s.payerCount}名（一般{s.flatCount}・役職者{s.execCount}）／出席{s.budgetPax}名（招待含む）
        </p>
      </header>

      {/* 集金の進捗 */}
      <section className="border-b border-slate-800 px-4 py-3">
        <div className="flex items-baseline justify-between">
          <span className="text-xs text-slate-400">当日集金の進捗</span>
          <span className="text-sm font-bold tabular-nums">
            <span className="text-emerald-400">{yen(s.collected)}</span>
            <span className="text-slate-500"> / {yen(s.income)}円</span>
          </span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all"
            style={{ width: s.income > 0 ? `${(s.collected / s.income) * 100}%` : "0%" }}
          />
        </div>
        {s.adjustCount > 0 && (
          <p className="mt-2 text-[10px] text-amber-400">
            ※イレギュラー支払い {s.adjustCount}名・純増減 {s.adjustTotal >= 0 ? "＋" : "−"}
            {yen(Math.abs(s.adjustTotal))}円（規定額との差。収入合計に反映済み）
          </p>
        )}
      </section>

      {/* 収支表（予算／実績） */}
      <section className="border-b border-slate-800 py-2">
        <div className="grid grid-cols-[1fr_5.5rem_5.5rem] gap-2 px-4 py-1 text-[10px] text-slate-500">
          <span>■ 収支（円）</span>
          <span className="text-right">予算（見込）</span>
          <span className="text-right">実績（確定）</span>
        </div>
        <Row label="収入合計（会費＋ご支援金）" budget={yen(s.income)} actual={yen(s.income)} />
        <Row
          label="固定費合計"
          budget={yen(s.fixedBudget)}
          actual={s.hasActual ? yen(s.fixedActual) : "―"}
        />
        <Row
          label="変動費合計"
          budget={yen(s.variableBudget)}
          actual={s.hasActual ? yen(s.variableActual) : "―"}
        />
        <Row
          label="差引残高（余剰金）"
          budget={yen(s.surplusBudget)}
          actual={s.surplusActual !== null ? yen(s.surplusActual) : "―"}
          strong
          color={
            (s.surplusActual ?? s.surplusBudget) < 0 ? "text-rose-400" : "text-emerald-400"
          }
        />
      </section>

      {/* 返金配分 */}
      <section className="border-b border-slate-800 py-2">
        <div className="px-4 py-1 text-[10px] text-slate-500">■ 返金配分</div>
        <Row
          label={`一般（${s.flatCount}名・一律 上限${yen(event?.refund_flat ?? 0)}円）`}
          budget={yen(s.refundFlatBudget)}
          actual={s.refundFlatActual !== null ? yen(s.refundFlatActual) : "―"}
        />
        <p className="px-4 pt-1 text-[10px] text-slate-500">
          役職者（{s.execCount}名）は、実質負担が一般社員（
          {yen(useActual ? s.floorActual ?? s.floorBudget : s.floorBudget)}円）を下回らない範囲で、
          負担額の高い役職から多めに返金します（逆転しません）。金額は下の実質負担でご確認ください。
        </p>
        {s.refundFlatReduced && (
          <p className="px-4 py-1 text-[10px] text-amber-400">
            ※余剰金が不足のため一般返金は設定額から自動減額されています
          </p>
        )}
        {leftover > 0 && (
          <p className="px-4 py-1 text-[10px] text-amber-400">
            ※役職者を全員一般社員と同額まで下げても {yen(leftover)}円 余ります（返しきれない余剰）。
            一般返金額（上限）を上げるか、記念品等に充当してください。
          </p>
        )}
      </section>

      {/* 役職別 実質負担 */}
      <section className="py-2">
        <div className="px-4 py-1 text-[10px] text-slate-500">
          ■ 役職別 実質負担（{s.hasActual ? "実績" : "予算"}ベース・返金差引後）
        </div>
        <ul className="divide-y divide-slate-800/60">
          {ranks.map((r) => {
            const rankDue = r.fee + r.support;
            const refund = rankRefund(rankDue, r.grp, s, useActual);
            const burden = Math.max(0, rankDue - refund);
            const count = attendees.filter(
              (a) => a.rank === r.name && a.rank !== "欠席"
            ).length;
            return (
              <li
                key={r.id}
                className="grid grid-cols-[1fr_4.5rem_6rem] items-center gap-2 px-4 py-1.5"
              >
                <span className="text-xs">
                  {r.name}
                  <span className="ml-1 text-[10px] text-slate-500">
                    （{r.grp === "flat" ? "一般" : "役職者"}・{count}名）
                  </span>
                </span>
                <span className="text-right text-[10px] tabular-nums text-slate-500">
                  {refund > 0 ? `返金${yen(refund)}` : ""}
                </span>
                <span className="text-right text-sm font-bold tabular-nums">
                  {yen(burden)}円
                </span>
              </li>
            );
          })}
        </ul>
        <p className="px-4 py-4 text-center text-[10px] text-slate-600">
          「予算」＝1人当たり予算×出席者数（招待含む）の見込み。「実績」＝入力済みの実費からの確定額。端数切捨て。
        </p>
      </section>
    </div>
  );
}
