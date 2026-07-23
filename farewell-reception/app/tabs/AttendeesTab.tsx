"use client";

// 参加者管理タブ：追加・編集・削除。役職を選ぶと会費・ご支援金を自動設定
import { useMemo, useState } from "react";
import type { Attendee, Rank } from "../types";
import { SPECIAL_RANKS } from "../types";
import { yen } from "../calc";

type Draft = {
  id: number | null; // null=新規
  dept: string;
  name: string;
  rank: string;
  fee: number;
  support: number;
  alcohol: string;
  shuttle: string;
  note: string;
};

const emptyDraft = (rank: string): Draft => ({
  id: null,
  dept: "",
  name: "",
  rank,
  fee: 0,
  support: 0,
  alcohol: "なし",
  shuttle: "なし",
  note: "",
});

export default function AttendeesTab({
  list,
  ranks,
  setList,
}: {
  list: Attendee[];
  ranks: Rank[];
  setList: (v: Attendee[]) => void;
}) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);

  const rankNames = useMemo(
    () => [...ranks.map((r) => r.name), ...SPECIAL_RANKS],
    [ranks]
  );

  const groups = useMemo(() => {
    const active = list.filter((a) => a.rank !== "欠席");
    const absent = list.filter((a) => a.rank === "欠席");
    return { active, absent };
  }, [list]);

  function openNew() {
    setDraft(emptyDraft(ranks[0]?.name ?? ""));
    applyRankFee(ranks[0]?.name ?? "", emptyDraft(ranks[0]?.name ?? ""));
  }
  function openEdit(a: Attendee) {
    setDraft({
      id: a.id,
      dept: a.dept,
      name: a.name,
      rank: a.rank,
      fee: a.fee,
      support: a.support,
      alcohol: a.alcohol || "なし",
      shuttle: a.shuttle || "なし",
      note: a.note,
    });
  }

  // 役職を選んだら会費・支援金を会費テーブルから自動設定
  function applyRankFee(rankName: string, base?: Draft) {
    const d = base ?? draft;
    if (!d) return;
    const r = ranks.find((x) => x.name === rankName);
    const fee = r?.fee ?? 0;
    const support = r?.support ?? 0;
    setDraft({ ...d, rank: rankName, fee, support });
  }

  async function save() {
    if (!draft) return;
    if (!draft.name.trim()) {
      alert("氏名を入力してください");
      return;
    }
    setBusy(true);
    const payload = {
      dept: draft.dept,
      name: draft.name,
      rank: draft.rank,
      fee: draft.fee,
      support: draft.support,
      due: draft.fee + draft.support,
      alcohol: draft.alcohol,
      shuttle: draft.shuttle,
      note: draft.note,
    };
    try {
      const res = await fetch(
        draft.id === null ? "/api/attendees" : `/api/attendees/${draft.id}`,
        {
          method: draft.id === null ? "POST" : "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      const data = (await res.json()) as { ok?: boolean; attendee?: Attendee; error?: string };
      if (!res.ok || !data.attendee) throw new Error(data.error ?? "保存に失敗しました");
      if (draft.id === null) {
        setList([...list, data.attendee]);
      } else {
        setList(list.map((a) => (a.id === draft.id ? data.attendee! : a)));
      }
      setDraft(null);
    } catch (e) {
      alert(e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function remove(a: Attendee) {
    if (!window.confirm(`${a.name} さんを削除しますか？（受付・集金の記録も消えます）`)) return;
    try {
      const res = await fetch(`/api/attendees/${a.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error();
      setList(list.filter((x) => x.id !== a.id));
      setDraft(null);
    } catch {
      alert("削除に失敗しました");
    }
  }

  const Row = ({ a }: { a: Attendee }) => (
    <li key={a.id}>
      <button
        onClick={() => openEdit(a)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left active:bg-slate-900"
      >
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-bold">
            {a.dept && <span className="mr-1 text-[10px] text-slate-400">{a.dept}</span>}
            {a.name}
          </span>
          <span className="block text-[10px] text-slate-400">
            {a.rank}
            {a.alcohol === "あり" && " ・🍺"}
            {a.shuttle === "あり" && " ・🚐"}
            {a.note && ` ・${a.note}`}
          </span>
        </span>
        <span className="shrink-0 text-right">
          <span className="block text-sm font-bold tabular-nums">
            {a.due > 0 ? `${yen(a.due)}円` : a.rank === "招待" ? "招待" : "0円"}
          </span>
          {a.support > 0 && (
            <span className="block text-[10px] text-slate-500">
              会費{yen(a.fee)}＋支援{yen(a.support)}
            </span>
          )}
        </span>
        <span className="shrink-0 text-slate-600">›</span>
      </button>
    </li>
  );

  return (
    <div>
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-700 bg-slate-900/95 px-4 py-3 backdrop-blur">
        <h1 className="text-sm font-bold text-amber-400">参加者管理（{groups.active.length}名）</h1>
        <button
          onClick={openNew}
          className="rounded-lg bg-amber-500 px-3 py-2 text-xs font-bold text-slate-900"
        >
          ＋ 追加
        </button>
      </header>

      <ul className="divide-y divide-slate-800">
        {groups.active.map((a) => (
          <Row key={a.id} a={a} />
        ))}
      </ul>

      {groups.absent.length > 0 && (
        <>
          <div className="bg-slate-900 px-4 py-1.5 text-[10px] text-slate-500">
            欠席（{groups.absent.length}名）
          </div>
          <ul className="divide-y divide-slate-800 opacity-60">
            {groups.absent.map((a) => (
              <Row key={a.id} a={a} />
            ))}
          </ul>
        </>
      )}

      <p className="px-4 py-6 text-center text-[10px] text-slate-600">
        行をタップで編集。役職を選ぶと会費・ご支援金が自動で入ります。
      </p>

      {/* 編集モーダル */}
      {draft && (
        <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 sm:items-center">
          <div className="max-h-[90dvh] w-full max-w-md overflow-y-auto rounded-t-2xl bg-slate-900 p-4 sm:rounded-2xl">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-bold">
                {draft.id === null ? "参加者を追加" : "参加者を編集"}
              </h2>
              <button onClick={() => setDraft(null)} className="px-2 text-slate-400">
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div className="flex gap-2">
                <label className="w-24 shrink-0">
                  <span className="text-[10px] text-slate-400">部署</span>
                  <input
                    value={draft.dept}
                    onChange={(e) => setDraft({ ...draft, dept: e.target.value })}
                    placeholder="生技"
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  />
                </label>
                <label className="min-w-0 flex-1">
                  <span className="text-[10px] text-slate-400">氏名（必須）</span>
                  <input
                    value={draft.name}
                    onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                    placeholder="山田"
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  />
                </label>
              </div>

              <label className="block">
                <span className="text-[10px] text-slate-400">区分（役職）</span>
                <select
                  value={draft.rank}
                  onChange={(e) => applyRankFee(e.target.value)}
                  className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                >
                  {rankNames.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </label>

              <div className="flex gap-2">
                <label className="flex-1">
                  <span className="text-[10px] text-slate-400">会費（円）</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    value={draft.fee}
                    onChange={(e) =>
                      setDraft({ ...draft, fee: Math.max(0, Number(e.target.value) || 0) })
                    }
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  />
                </label>
                <label className="flex-1">
                  <span className="text-[10px] text-slate-400">ご支援金（円）</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    value={draft.support}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        support: Math.max(0, Number(e.target.value) || 0),
                      })
                    }
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  />
                </label>
                <div className="flex-1">
                  <span className="text-[10px] text-slate-400">徴収額（自動）</span>
                  <div className="rounded-lg bg-slate-800/50 px-2 py-2 text-sm font-bold tabular-nums">
                    {yen(draft.fee + draft.support)}円
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <label className="flex-1">
                  <span className="text-[10px] text-slate-400">🍺 アルコール</span>
                  <select
                    value={draft.alcohol}
                    onChange={(e) => setDraft({ ...draft, alcohol: e.target.value })}
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  >
                    <option>なし</option>
                    <option>あり</option>
                  </select>
                </label>
                <label className="flex-1">
                  <span className="text-[10px] text-slate-400">🚐 送迎</span>
                  <select
                    value={draft.shuttle}
                    onChange={(e) => setDraft({ ...draft, shuttle: e.target.value })}
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  >
                    <option>なし</option>
                    <option>あり</option>
                  </select>
                </label>
              </div>

              <label className="block">
                <span className="text-[10px] text-slate-400">備考（食事制限など）</span>
                <input
                  value={draft.note}
                  onChange={(e) => setDraft({ ...draft, note: e.target.value })}
                  className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                />
              </label>

              <div className="flex gap-2 pt-1">
                {draft.id !== null && (
                  <button
                    onClick={() => {
                      const a = list.find((x) => x.id === draft.id);
                      if (a) remove(a);
                    }}
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
