// 収支サマリー・返金計算（Excelの収支管理シートと同じロジック）
import type { Attendee, EventRow, Expense, Rank } from "./types";

export type Summary = {
  payerCount: number; // 会費負担者（招待・欠席を除く）＝返金の分母
  budgetPax: number; // 出席者（招待含む・欠席除く）＝1人当たり予算の分母
  flatCount: number; // 一般グループ人数
  execCount: number; // 役職者グループ人数
  income: number; // 収入合計（会費＋ご支援金）
  collected: number; // 集金済み合計（参考）
  fixedBudget: number;
  fixedActual: number;
  variableBudget: number;
  variableActual: number;
  expenseBudget: number; // 費用予算合計
  expenseActual: number; // 費用実績合計
  hasActual: boolean; // 実績が1件でも入力されているか
  surplusBudget: number; // 余剰金（予算ベース）
  surplusActual: number | null; // 余剰金（実績ベース。実績未入力ならnull）
  refundFlatBudget: number; // 一般1人あたり返金（予算）
  refundFlatActual: number | null;
  refundExecBudget: number; // 役職者1人あたり返金（予算）
  refundExecActual: number | null;
  refundFlatReduced: boolean; // 設定額から自動減額されたか（予算ベース）
};

export function expenseBudgetOf(e: Expense, budgetPax: number): number {
  if (e.budget_total !== null && e.budget_total !== undefined) return e.budget_total;
  if (e.budget_pp !== null && e.budget_pp !== undefined) return e.budget_pp * budgetPax;
  return 0;
}

export function computeSummary(
  attendees: Attendee[],
  ranks: Rank[],
  expenses: Expense[],
  event: EventRow | null
): Summary {
  const flatRanks = new Set(ranks.filter((r) => r.grp === "flat").map((r) => r.name));
  const execRanks = new Set(ranks.filter((r) => r.grp === "exec").map((r) => r.name));

  const present = attendees.filter((a) => a.rank !== "欠席");
  const payers = present.filter((a) => a.rank !== "招待");
  const flatCount = payers.filter((a) => flatRanks.has(a.rank)).length;
  const execCount = payers.filter((a) => execRanks.has(a.rank)).length;

  const income = payers.reduce((s, a) => s + a.due, 0);
  const collected = payers.filter((a) => a.paid).reduce((s, a) => s + a.due, 0);

  const budgetPax = present.length;
  const fixed = expenses.filter((e) => e.kind === "fixed");
  const variable = expenses.filter((e) => e.kind === "variable");
  const sumBudget = (list: Expense[]) =>
    list.reduce((s, e) => s + expenseBudgetOf(e, budgetPax), 0);
  const sumActual = (list: Expense[]) => list.reduce((s, e) => s + (e.actual ?? 0), 0);

  const fixedBudget = sumBudget(fixed);
  const variableBudget = sumBudget(variable);
  const fixedActual = sumActual(fixed);
  const variableActual = sumActual(variable);
  const expenseBudget = fixedBudget + variableBudget;
  const expenseActual = fixedActual + variableActual;
  const hasActual = expenses.some((e) => e.actual !== null && e.actual !== undefined);

  const surplusBudget = income - expenseBudget;
  const surplusActual = hasActual ? income - expenseActual : null;

  // 返金：一般=設定額が上限（余剰不足なら自動減額）、役職者=残額を按分（切捨て）
  const setting = Math.max(0, event?.refund_flat ?? 0);
  const calcRefunds = (surplus: number) => {
    const flatCap =
      flatCount > 0 ? Math.max(0, Math.floor(surplus / flatCount)) : 0;
    const flat = surplus <= 0 || flatCount === 0 ? 0 : Math.min(setting, flatCap);
    const rest = surplus - flat * flatCount;
    const exec = execCount > 0 ? Math.max(0, Math.floor(rest / execCount)) : 0;
    return { flat, exec };
  };
  const b = calcRefunds(surplusBudget);
  const a = surplusActual !== null ? calcRefunds(surplusActual) : null;

  return {
    payerCount: payers.length,
    budgetPax,
    flatCount,
    execCount,
    income,
    collected,
    fixedBudget,
    fixedActual,
    variableBudget,
    variableActual,
    expenseBudget,
    expenseActual,
    hasActual,
    surplusBudget,
    surplusActual,
    refundFlatBudget: b.flat,
    refundFlatActual: a?.flat ?? null,
    refundExecBudget: b.exec,
    refundExecActual: a?.exec ?? null,
    refundFlatReduced: setting > 0 && b.flat < setting,
  };
}

export const yen = (n: number) => n.toLocaleString("ja-JP");
