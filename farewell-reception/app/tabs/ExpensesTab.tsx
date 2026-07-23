"use client";

// 費用管理タブ：固定費・変動費。予算（1人当たり or 総額）と実績を入力
import { useMemo, useState } from "react";
import type { Attendee, Expense } from "../types";
import { expenseBudgetOf, yen } from "../calc";

type Draft = {
  id: number | null;
  kind: "fixed" | "variable";
  name: string;
  budget_pp: string; // 入力欄は文字列（空=null）
  budget_total: string;
  actual: string;
  note: string;
};

const toDraft = (e: Expense): Draft => ({
  id: e.id,
  kind: e.kind,
  name: e.name,
  budget_pp: e.budget_pp === null ? "" : String(e.budget_pp),
  budget_total: e.budget_total === null ? "" : String(e.budget_total),
  actual: e.actual === null ? "" : String(e.actual),
  note: e.note,
});

export default function ExpensesTab({
  expenses,
  attendees,
  setExpenses,
}: {
  expenses: Expense[];
  attendees: Attendee[];
  setExpenses: (v: Expense[]) => void;
}) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);

  // 予算の分母＝出席者数（招待含む・欠席除く）
  const budgetPax = useMemo(
    () => attendees.filter((a) => a.rank !== "欠席").length,
    [attendees]
  );

  const fixed = expenses.filter((e) => e.kind === "fixed");
  const variable = expenses.filter((e) => e.kind === "variable");

  async function save() {
    if (!draft) return;
    if (!draft.name.trim()) {
      alert("項目名を入力してください");
      return;
    }
    setBusy(true);
    const num = (s: string) => (s.trim() === "" ? null : Math.max(0, Number(s) || 0));
    const payload = {
      kind: draft.kind,
      name: draft.name,
      budget_pp: num(draft.budget_pp),
      budget_total: num(draft.budget_total),
      actual: num(draft.actual),
      note: draft.note,
    };
    try {
      const res = await fetch(
        draft.id === null ? "/api/expenses" : `/api/expenses/${draft.id}`,
        {
          method: draft.id === null ? "POST" : "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      const data = (await res.json()) as { expense?: Expense; error?: string };
      if (!res.ok || !data.expense) throw new Error(data.error ?? "保存に失敗しました");
      if (draft.id === null) {
        setExpenses([...expenses, data.expense]);
      } else {
        setExpenses(expenses.map((e) => (e.id === draft.id ? data.expense! : e)));
      }
      setDraft(null);
    } catch (e) {
      alert(e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!window.confirm("この費用項目を削除しますか？")) return;
    try {
      const res = await fetch(`/api/expenses/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error();
      setExpenses(expenses.filter((e) => e.id !== id));
      setDraft(null);
    } catch {
      alert("削除に失敗しました");
    }
  }

  const Section = ({ title, list, kind }: { title: string; list: Expense[]; kind: "fixed" | "variable" }) => {
    const budgetSum = list.reduce((s, e) => s + expenseBudgetOf(e, budgetPax), 0);
    const actualSum = list.reduce((s, e) => s + (e.actual ?? 0), 0);
    return (
      <section className="mb-4">
        <div className="flex items-center justify-between px-4 py-2">
          <h2 className="text-xs font-bold text-slate-300">{title}</h2>
          <button
            onClick={() =>
              setDraft({ id: null, kind, name: "", budget_pp: "", budget_total: "", actual: "", note: "" })
            }
            className="rounded bg-slate-800 px-2 py-1 text-[10px] font-bold text-amber-400"
          >
            ＋ 項目追加
          </button>
        </div>
        <ul className="divide-y divide-slate-800 border-y border-slate-800">
          {list.map((e) => {
            const budget = expenseBudgetOf(e, budgetPax);
            return (
              <li key={e.id}>
                <button
                  onClick={() => setDraft(toDraft(e))}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left active:bg-slate-900"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">{e.name}</span>
                    <span className="block text-[10px] text-slate-500">
                      {e.budget_total !== null
                        ? `総額予算 ${yen(e.budget_total)}円`
                        : e.budget_pp !== null
                          ? `1人${yen(e.budget_pp)}円 × ${budgetPax}名`
                          : "予算未入力"}
                      {e.note && ` ・${e.note}`}
                    </span>
                  </span>
                  <span className="shrink-0 text-right tabular-nums">
                    <span className="block text-sm font-bold">
                      {budget > 0 ? `${yen(budget)}円` : "―"}
                    </span>
                    <span
                      className={`block text-[10px] ${
                        e.actual !== null ? "text-emerald-400" : "text-slate-600"
                      }`}
                    >
                      実績 {e.actual !== null ? `${yen(e.actual)}円` : "未入力"}
                    </span>
                  </span>
                  <span className="shrink-0 text-slate-600">›</span>
                </button>
              </li>
            );
          })}
          {list.length === 0 && (
            <li className="px-4 py-4 text-center text-xs text-slate-600">項目がありません</li>
          )}
        </ul>
        <div className="flex justify-end gap-4 px-4 py-1.5 text-[11px] tabular-nums text-slate-400">
          <span>予算計 <b className="text-slate-200">{yen(budgetSum)}円</b></span>
          <span>実績計 <b className="text-emerald-400">{yen(actualSum)}円</b></span>
        </div>
      </section>
    );
  };

  return (
    <div>
      <header className="sticky top-0 z-10 border-b border-slate-700 bg-slate-900/95 px-4 py-3 backdrop-blur">
        <h1 className="text-sm font-bold text-amber-400">費用管理</h1>
        <p className="mt-0.5 text-[10px] text-slate-500">
          1人当たり予算は出席者{budgetPax}名（招待含む）を掛けて予算合計を計算します
        </p>
      </header>

      <div className="py-3">
        <Section title="■ 固定費（記念品・バス代など）" list={fixed} kind="fixed" />
        <Section title="■ 変動費（食事代・飲み放題など）" list={variable} kind="variable" />
      </div>

      {/* 編集モーダル */}
      {draft && (
        <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 sm:items-center">
          <div className="w-full max-w-md rounded-t-2xl bg-slate-900 p-4 sm:rounded-2xl">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-bold">
                {draft.id === null ? "費用項目を追加" : "費用項目を編集"}
                <span className="ml-2 text-[10px] text-slate-500">
                  （{draft.kind === "fixed" ? "固定費" : "変動費"}）
                </span>
              </h2>
              <button onClick={() => setDraft(null)} className="px-2 text-slate-400">
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <label className="block">
                <span className="text-[10px] text-slate-400">項目名（必須）</span>
                <input
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                  placeholder="食事代"
                  className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                />
              </label>

              <div className="flex gap-2">
                <label className="flex-1">
                  <span className="text-[10px] text-slate-400">1人当たり予算</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    value={draft.budget_pp}
                    onChange={(e) => setDraft({ ...draft, budget_pp: e.target.value })}
                    placeholder="空欄可"
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  />
                </label>
                <label className="flex-1">
                  <span className="text-[10px] text-slate-400">総額予算（優先）</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    value={draft.budget_total}
                    onChange={(e) => setDraft({ ...draft, budget_total: e.target.value })}
                    placeholder="空欄可"
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  />
                </label>
              </div>

              <label className="block">
                <span className="text-[10px] text-slate-400">実績（円）— 支払い後に入力</span>
                <input
                  type="number"
                  inputMode="numeric"
                  value={draft.actual}
                  onChange={(e) => setDraft({ ...draft, actual: e.target.value })}
                  placeholder="空欄=未確定"
                  className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                />
              </label>

              <label className="block">
                <span className="text-[10px] text-slate-400">備考</span>
                <input
                  value={draft.note}
                  onChange={(e) => setDraft({ ...draft, note: e.target.value })}
                  className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                />
              </label>

              <div className="flex gap-2 pt-1">
                {draft.id !== null && (
                  <button
                    onClick={() => remove(draft.id!)}
                    className="rounded-lg bg-rose-500/20 px-3 py-2.5 text-xs font-bold text-rose-300"
                  >
                    削除
                  </button>
                )}
                <button
                  onClick={save}
                  disabled={busy}
                  className="flex-1 rounded-lg bg-amber-500 py-2.5 text-sm font-bold text-slate-900 disabled:opacity-50"
                >
                  {busy ? "保存中…" : "保存"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
