import { getCloudflareContext } from "@opennextjs/cloudflare";
import type { NextRequest } from "next/server";
import type { Expense } from "../../../types";
import { jsonError } from "../../lib";

export const dynamic = "force-dynamic";

// 費用項目の更新（予算・実績・名前。null指定でクリア可）
export async function PATCH(
  req: NextRequest,
  ctx: RouteContext<"/api/expenses/[id]">
) {
  const { id } = await ctx.params;
  const expenseId = Number(id);
  if (!Number.isInteger(expenseId)) return jsonError("invalid id");

  const body = (await req.json()) as Partial<Expense>;
  const sets: string[] = [];
  const values: (number | string | null)[] = [];

  if (typeof body.name === "string" && body.name.trim() !== "") {
    sets.push("name = ?");
    values.push(body.name.trim());
  }
  if (typeof body.note === "string") {
    sets.push("note = ?");
    values.push(body.note);
  }
  for (const key of ["budget_pp", "budget_total", "actual"] as const) {
    if (key in body) {
      const v = body[key];
      if (v === null) {
        sets.push(`${key} = NULL`);
      } else if (typeof v === "number" && Number.isFinite(v) && v >= 0) {
        sets.push(`${key} = ?`);
        values.push(Math.round(v));
      }
    }
  }
  if (sets.length === 0) return jsonError("nothing to update");

  values.push(expenseId);
  const { env } = getCloudflareContext();
  await env.DB.prepare(`UPDATE expenses SET ${sets.join(", ")} WHERE id = ?`)
    .bind(...values)
    .run();
  const row = await env.DB.prepare("SELECT * FROM expenses WHERE id = ?")
    .bind(expenseId)
    .first<Expense>();
  return Response.json({ ok: true, expense: row });
}

// 費用項目を削除
export async function DELETE(
  _req: NextRequest,
  ctx: RouteContext<"/api/expenses/[id]">
) {
  const { id } = await ctx.params;
  const expenseId = Number(id);
  if (!Number.isInteger(expenseId)) return jsonError("invalid id");

  const { env } = getCloudflareContext();
  await env.DB.prepare("DELETE FROM expenses WHERE id = ?")
    .bind(expenseId)
    .run();
  return Response.json({ ok: true });
}
