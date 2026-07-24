// 収支サマリー・返金計算（Excelの収支管理シートと同じロジック）
import type { Attendee, EventRow, Expense, Rank } from "./types";

export type Summary = {
  payerCount: number; // 会費負担者（招待・欠席を除く）＝返金の分母
  budgetPax: number; // 出席者（招待含む・欠席除く）＝1人当たり予算の分母
  flatCount: number; // 一般グループ人数
  execCount: number; // 役職者グループ人数
  income: number; // 収入合計（会費＋ご支援金＋調整額）
  collected: number; // 集金済み合計（参考）
  adjustTotal: number; // 調整額の合計（イレギュラー支払いの純増減）
  adjustCount: number; // 調整額が入っている人数
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
  // 役職者の返金は「水位（level）方式」。各役職の返金 = max(0, 規定負担 − level)。
  // levelを下げるほど返金が増えるが、floor（＝一般社員の実質負担）を下回らない＝逆転防止
  execLevelBudget: number; // 役職者返金の水位（予算）
  execLevelActual: number | null;
  floorBudget: number; // 役職者負担の下限＝一般実質負担（予算）
  floorActual: number | null;
  execLeftoverBudget: number; // 全役職者がfloorに達しても返しきれない余剰（予算）
  execLeftoverActual: number | null;
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
  const adjustTotal = payers.reduce((s, a) => s + (a.adjust ?? 0), 0);
  const adjustCount = payers.filter((a) => (a.adjust ?? 0) !== 0).length;

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

  // 返金ロジック（逆転防止）：
  //  ① 一般（flat）に設定額を一律返金（余剰不足なら自動減額）
  //  ② 残りを役職者（exec）に配分。ただし各役職者の実質負担が一般社員（floor）を下回らないよう、
  //     負担額の高い役職から「水位（level）」まで均等に下げる。各役職の返金 = max(0, 規定負担 − level)
  //     → 余剰が多ければ level が下がり上位役職ほど多く返金、floorで頭打ち（逆転しない）
  const setting = Math.max(0, event?.refund_flat ?? 0);
  // 一般社員の代表的な規定負担（会費＋ご支援金）。複数の一般役職があれば最大値を基準に
  const flatDueRep = ranks
    .filter((r) => r.grp === "flat")
    .reduce((m, r) => Math.max(m, r.fee + r.support), 0);
  // 役職者ひとりずつの規定負担（調整額は個人の任意上乗せなので返金基準に含めない）
  const execDues = payers
    .filter((a) => execRanks.has(a.rank))
    .map((a) => a.fee + a.support);
  const maxExecDue = execDues.length > 0 ? Math.max(...execDues) : 0;

  const calcRefunds = (surplus: number) => {
    // ① 一般返金
    const flatCap = flatCount > 0 ? Math.max(0, Math.floor(surplus / flatCount)) : 0;
    const flat = surplus <= 0 || flatCount === 0 ? 0 : Math.min(setting, flatCap);
    // 役職者負担の下限＝一般社員の実質負担
    const floor = Math.max(0, flatDueRep - flat);
    // ② 役職者に配分できる残額
    const execBudget = Math.max(0, surplus - flat * flatCount);

    let level = maxExecDue > floor ? maxExecDue : floor; // 返金0のとき水位＝最大負担
    let leftover = 0;
    if (execDues.length > 0 && execBudget > 0) {
      // 全員floorまで下げるのに必要な額
      const maxReturn = execDues.reduce((s, d) => s + Math.max(0, d - floor), 0);
      if (execBudget >= maxReturn) {
        level = floor; // 全役職者が一般社員と同額まで下がる
        leftover = execBudget - maxReturn; // それでも余る分（役職者には返しきれない）
      } else {
        // 二分探索：Σ max(0, due − level) = execBudget となる level（floor以上）
        let lo = floor;
        let hi = maxExecDue;
        for (let i = 0; i < 60; i++) {
          const mid = (lo + hi) / 2;
          const ret = execDues.reduce((s, d) => s + Math.max(0, d - mid), 0);
          if (ret > execBudget) lo = mid;
          else hi = mid;
        }
        level = hi;
      }
    }
    return { flat, level, floor, leftover };
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
    adjustTotal,
    adjustCount,
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
    execLevelBudget: b.level,
    execLevelActual: a?.level ?? null,
    floorBudget: b.floor,
    floorActual: a?.floor ?? null,
    execLeftoverBudget: b.leftover,
    execLeftoverActual: a?.leftover ?? null,
    refundFlatReduced: setting > 0 && b.flat < setting,
  };
}

// 役職の返金額（1人あたり）。exec は水位方式で負担額に応じて変わる
export function rankRefund(
  rankDue: number, // その役職の規定負担（会費＋ご支援金）
  grp: "flat" | "exec",
  s: Summary,
  useActual: boolean
): number {
  if (grp === "flat") {
    const f = useActual ? s.refundFlatActual : s.refundFlatBudget;
    return f ?? 0;
  }
  const level = useActual ? s.execLevelActual : s.execLevelBudget;
  if (level === null || level === undefined) return 0;
  return Math.max(0, Math.floor(rankDue - level));
}

export const yen = (n: number) => n.toLocaleString("ja-JP");
