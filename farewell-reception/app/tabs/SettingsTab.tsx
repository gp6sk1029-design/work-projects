"use client";

// 設定タブ：イベント情報・役職別会費テーブル・返金設定・イベント切替/新規作成
import { useState } from "react";
import type { Attendee, EventRow, Rank } from "../types";
import type { Store } from "../AppShell";
import { yen } from "../calc";

export default function SettingsTab({
  store,
  setEvent,
  setRanks,
  setAttendees,
  reloadAll,
}: {
  store: Store;
  setEvent: (v: EventRow | null) => void;
  setRanks: (v: Rank[]) => void;
  setAttendees: (v: Attendee[]) => void;
  reloadAll: () => Promise<void>;
}) {
  const { event, events, ranks } = store;
  const [busy, setBusy] = useState(false);
  // 役職編集モーダル（会費・ご支援金・グループを1画面で編集）
  const [rankDraft, setRankDraft] = useState<{
    id: number;
    name: string;
    fee: number;
    support: number;
    grp: "flat" | "exec";
  } | null>(null);

  async function patchEvent(patch: Partial<EventRow>) {
    if (!event) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/events/${event.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      const data = (await res.json()) as { event?: EventRow; error?: string };
      if (!res.ok || !data.event) throw new Error(data.error ?? "保存に失敗しました");
      setEvent(data.event);
    } catch (e) {
      alert(e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  // 文字項目の編集（promptベースでシンプルに）
  function editText(key: keyof EventRow, label: string) {
    if (!event) return;
    const input = window.prompt(label, String(event[key] ?? ""));
    if (input === null) return;
    patchEvent({ [key]: input } as Partial<EventRow>);
  }

  function editRefundFlat() {
    if (!event) return;
    const input = window.prompt(
      "一般（一律返金グループ）1人あたり返金の設定額（円）\n※余剰金が足りない場合は自動で減額されます",
      String(event.refund_flat)
    );
    if (input === null) return;
    const v = Number(input.replace(/[^0-9]/g, ""));
    if (!Number.isFinite(v) || v < 0) return alert("0以上の数字で入力してください");
    patchEvent({ refund_flat: v });
  }

  // 役職の金額編集：モーダルを開く（会費・ご支援金・グループを1画面で）
  function editRank(r: Rank) {
    setRankDraft({ id: r.id, name: r.name, fee: r.fee, support: r.support, grp: r.grp });
  }

  // 役職モーダルの保存
  async function saveRank(applyToAttendees: boolean) {
    if (!rankDraft) return;
    if (!rankDraft.name.trim()) return alert("役職名を入力してください");
    setBusy(true);
    try {
      const res = await fetch(`/api/ranks/${rankDraft.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: rankDraft.name.trim(),
          fee: rankDraft.fee,
          support: rankDraft.support,
          grp: rankDraft.grp,
          applyToAttendees,
        }),
      });
      const data = (await res.json()) as { rank?: Rank; error?: string };
      if (!res.ok || !data.rank) throw new Error(data.error ?? "保存に失敗しました");
      setRanks(ranks.map((x) => (x.id === rankDraft.id ? data.rank! : x)));
      if (applyToAttendees) {
        const at = (await fetch("/api/attendees").then((x) => x.json())) as {
          attendees: Attendee[];
        };
        setAttendees(at.attendees);
      }
      setRankDraft(null);
    } catch (e) {
      alert(e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function toggleGrp(r: Rank) {
    const next = r.grp === "flat" ? "exec" : "flat";
    if (
      !window.confirm(
        `「${r.name}」を${next === "flat" ? "一般（一律返金）" : "役職者（按分返金）"}グループに変更しますか？`
      )
    )
      return;
    const res = await fetch(`/api/ranks/${r.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ grp: next, applyToAttendees: false }),
    });
    const data = (await res.json()) as { rank?: Rank };
    if (data.rank) setRanks(ranks.map((x) => (x.id === r.id ? data.rank! : x)));
  }

  async function addRank() {
    const name = window.prompt("追加する役職名");
    if (!name || !name.trim()) return;
    const res = await fetch("/api/ranks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim(), fee: 0, support: 0, grp: "flat" }),
    });
    const data = (await res.json()) as { rank?: Rank; error?: string };
    if (!res.ok || !data.rank) return alert(data.error ?? "追加に失敗しました");
    setRanks([...ranks, data.rank]);
  }

  async function removeRank(r: Rank) {
    if (!window.confirm(`役職「${r.name}」を削除しますか？`)) return;
    const res = await fetch(`/api/ranks/${r.id}`, { method: "DELETE" });
    const data = (await res.json()) as { ok?: boolean; error?: string };
    if (!res.ok) return alert(data.error ?? "削除に失敗しました");
    setRanks(ranks.filter((x) => x.id !== r.id));
  }

  // データのリセット（現在のイベント。次のイベント準備・使い回し用）
  async function resetData(target: "attendance" | "attendees" | "expenses") {
    const labels: Record<typeof target, string> = {
      attendance: "受付状況（来場・集金チェック）を全部クリア",
      attendees: "参加者リストを全員削除",
      expenses: "費用の項目を全部削除",
    };
    if (
      !window.confirm(
        `${labels[target]}します。\nこの操作は取り消せません。よろしいですか？`
      )
    )
      return;
    setBusy(true);
    try {
      const res = await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ targets: [target] }),
      });
      if (!res.ok) throw new Error("リセットに失敗しました");
      await reloadAll();
    } catch (e) {
      alert(e instanceof Error ? e.message : "リセットに失敗しました");
    } finally {
      setBusy(false);
    }
  }

  // 現在のイベントをJSONファイルに保存（ダウンロード）
  function exportEvent() {
    // ブラウザで直接ダウンロード（認証Cookieはfetchに乗るのでリンクでも可）
    window.location.href = "/api/export";
  }

  // JSONファイルを読み込んで新イベントとして復元
  async function importEvent(file: File) {
    if (
      !window.confirm(
        `「${file.name}」を読み込み、新しいイベントとして追加・切り替えますか？\n・現在のイベントは消えません（切替で戻れます）`
      )
    )
      return;
    setBusy(true);
    try {
      const text = await file.text();
      const res = await fetch("/api/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: text,
      });
      const data = (await res.json()) as {
        ok?: boolean;
        counts?: { attendees: number };
        error?: string;
      };
      if (!res.ok || !data.ok) throw new Error(data.error ?? "読み込みに失敗しました");
      await reloadAll();
      alert(`読み込みました（参加者 ${data.counts?.attendees ?? 0} 名）`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "読み込みに失敗しました");
    } finally {
      setBusy(false);
    }
  }

  // 新イベント作成（会費テーブルは現イベントからコピー）
  async function createEvent() {
    const title = window.prompt("新しいイベント名（例：田中さん 歓迎会）");
    if (!title || !title.trim()) return;
    if (
      !window.confirm(
        `「${title.trim()}」を作成して切り替えますか？\n・役職別会費テーブルは現在の設定をコピーします\n・参加者は空の状態から始まります\n・現在のイベントのデータはそのまま残ります（切替で戻れます）`
      )
    )
      return;
    setBusy(true);
    try {
      const res = await fetch("/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim() }),
      });
      if (!res.ok) throw new Error("作成に失敗しました");
      await reloadAll();
    } catch (e) {
      alert(e instanceof Error ? e.message : "作成に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function activateEvent(ev: EventRow) {
    if (ev.is_active === 1) return;
    if (!window.confirm(`「${ev.title}」に切り替えますか？`)) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/events/${ev.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activate: true }),
      });
      if (!res.ok) throw new Error("切替に失敗しました");
      await reloadAll();
    } catch (e) {
      alert(e instanceof Error ? e.message : "切替に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  // イベントを削除（参加者・費用ごと）
  async function deleteEvent(ev: EventRow) {
    const n = ev.id === event?.id ? store.attendees.length : null;
    if (
      !window.confirm(
        `イベント「${ev.title}」（${ev.event_date || "日付未設定"}）を削除しますか？\n` +
          `参加者・費用・受付結果も一緒に消えます。取り消せません。\n` +
          (ev.is_active === 1 ? "※運用中のイベントです。削除すると別のイベントに切り替わります。" : "") +
          (n ? `\n（参加者 ${n} 名）` : "")
      )
    )
      return;
    setBusy(true);
    try {
      const res = await fetch(`/api/events/${ev.id}`, { method: "DELETE" });
      const data = (await res.json()) as { ok?: boolean; error?: string };
      if (!res.ok || !data.ok) throw new Error(data.error ?? "削除に失敗しました");
      await reloadAll();
    } catch (e) {
      alert(e instanceof Error ? e.message : "削除に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  const InfoRow = ({ label, value, onEdit }: { label: string; value: string; onEdit: () => void }) => (
    <button
      onClick={onEdit}
      className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left active:bg-slate-900"
    >
      <span className="shrink-0 text-xs text-slate-400">{label}</span>
      <span className="min-w-0 flex-1 truncate text-right text-sm">{value || "―"}</span>
      <span className="shrink-0 text-slate-600">›</span>
    </button>
  );

  return (
    <div className={busy ? "pointer-events-none opacity-60" : ""}>
      <header className="sticky top-0 z-10 border-b border-slate-700 bg-slate-900/95 px-4 py-3 backdrop-blur">
        <h1 className="text-sm font-bold text-amber-400">設定</h1>
      </header>

      {event ? (
        <>
          {/* イベント情報 */}
          <section className="border-b border-slate-800 py-1">
            <div className="px-4 py-1 text-[10px] text-slate-500">■ イベント情報（タップで編集）</div>
            <div className="divide-y divide-slate-800/60">
              <InfoRow label="イベント名" value={event.title} onEdit={() => editText("title", "イベント名")} />
              <InfoRow label="種別" value={event.event_type} onEdit={() => editText("event_type", "種別（居酒屋/バーベキュー など）")} />
              <InfoRow label="開催日" value={event.event_date} onEdit={() => editText("event_date", "開催日（例：2026-07-30）")} />
              <InfoRow label="幹事" value={event.organizer} onEdit={() => editText("organizer", "幹事名")} />
              <InfoRow label="会場" value={event.venue} onEdit={() => editText("venue", "会場（店名）")} />
              <InfoRow label="住所" value={event.venue_addr} onEdit={() => editText("venue_addr", "会場住所")} />
              <InfoRow label="URL" value={event.venue_url} onEdit={() => editText("venue_url", "会場URL")} />
            </div>
          </section>

          {/* 役職別会費テーブル */}
          <section className="border-b border-slate-800 py-1">
            <div className="flex items-center justify-between px-4 py-1">
              <span className="text-[10px] text-slate-500">
                ■ 役職別 会費・ご支援金（タップで金額編集／グループ名タップで一般⇔役職者切替）
              </span>
              <button onClick={addRank} className="rounded bg-slate-800 px-2 py-1 text-[10px] font-bold text-amber-400">
                ＋ 役職追加
              </button>
            </div>
            <ul className="divide-y divide-slate-800/60">
              {ranks.map((r) => (
                <li key={r.id} className="flex items-center gap-1 px-4 py-1.5">
                  <button onClick={() => editRank(r)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
                    <span className="w-12 shrink-0 text-sm">{r.name}</span>
                    <span className="flex-1 text-right text-xs tabular-nums text-slate-300">
                      会費 {yen(r.fee)}
                      {r.support > 0 && <span className="text-slate-500"> ＋支援 {yen(r.support)}</span>}
                      <span className="ml-1 font-bold">＝{yen(r.fee + r.support)}円</span>
                    </span>
                  </button>
                  <button
                    onClick={() => toggleGrp(r)}
                    className={`w-14 shrink-0 rounded px-1 py-1 text-center text-[10px] font-bold ${
                      r.grp === "flat" ? "bg-sky-500/20 text-sky-300" : "bg-purple-500/20 text-purple-300"
                    }`}
                  >
                    {r.grp === "flat" ? "一般" : "役職者"}
                  </button>
                  <button
                    onClick={() => removeRank(r)}
                    className="w-7 shrink-0 text-center text-xs text-slate-600 active:text-rose-400"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          </section>

          {/* 返金設定 */}
          <section className="border-b border-slate-800 py-1">
            <div className="px-4 py-1 text-[10px] text-slate-500">■ 返金設定</div>
            <InfoRow
              label="一般 1人あたり返金（上限）"
              value={`${yen(event.refund_flat)}円`}
              onEdit={editRefundFlat}
            />
            <p className="px-4 pb-2 text-[10px] text-slate-600">
              余剰金からこの金額を一般（一律返金グループ）に返金し、残額を役職者で按分します。不足時は自動減額。
            </p>
          </section>
        </>
      ) : (
        <p className="px-4 py-6 text-center text-sm text-slate-500">アクティブなイベントがありません</p>
      )}

      {/* イベント一覧・切替・新規作成 */}
      <section className="py-1">
        <div className="flex items-center justify-between px-4 py-1">
          <span className="text-[10px] text-slate-500">■ イベント一覧（タップで切替）</span>
          <button onClick={createEvent} className="rounded bg-amber-500 px-2 py-1 text-[10px] font-bold text-slate-900">
            ＋ 新しいイベント
          </button>
        </div>
        <ul className="divide-y divide-slate-800/60">
          {events.map((ev) => (
            <li key={ev.id} className="flex items-center">
              <button
                onClick={() => activateEvent(ev)}
                className="flex min-w-0 flex-1 items-center gap-2 px-4 py-2.5 text-left active:bg-slate-900"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm">{ev.title}</span>
                  <span className="block text-[10px] text-slate-500">{ev.event_date || "日付未設定"}</span>
                </span>
                {ev.is_active === 1 ? (
                  <span className="shrink-0 rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                    運用中
                  </span>
                ) : (
                  <span className="shrink-0 text-[10px] text-slate-600">切替 ›</span>
                )}
              </button>
              {events.length > 1 && (
                <button
                  onClick={() => deleteEvent(ev)}
                  aria-label={`${ev.title}を削除`}
                  className="mr-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-500 active:bg-rose-500/20 active:text-rose-300"
                >
                  🗑
                </button>
              )}
            </li>
          ))}
        </ul>
        <p className="px-4 py-4 text-center text-[10px] text-slate-600">
          切替でいつでも戻れます。🗑で不要なイベントを削除（参加者・費用ごと消えます／取り消し不可）。
          次回の歓送迎会は「＋新しいイベント」から。
        </p>
      </section>

      {/* データの保存・読み込み（バックアップ／過去イベントの振り返り） */}
      <section className="border-t border-slate-800 py-1">
        <div className="px-4 py-1 text-[10px] text-slate-500">■ データの保存・読み込み</div>
        <div className="flex gap-2 px-4 py-2">
          <button
            onClick={exportEvent}
            className="flex-1 rounded-lg bg-slate-800 py-2.5 text-xs font-bold text-sky-300"
          >
            💾 このイベントを保存（ファイル）
          </button>
          <label className="flex-1 cursor-pointer rounded-lg bg-slate-800 py-2.5 text-center text-xs font-bold text-emerald-300">
            📂 ファイルを読み込み
            <input
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) importEvent(f);
                e.target.value = "";
              }}
            />
          </label>
        </div>
        <p className="px-4 pb-2 text-[10px] text-slate-600">
          「保存」でイベント一式（参加者・費用・受付結果）をファイルに書き出します。別PCへの移動や
          バックアップ、過去イベントの振り返りに。読み込むと新しいイベントとして復元します（現在のデータは消えません）。
        </p>
      </section>

      {/* データのリセット（次のイベント準備・使い回し） */}
      <section className="border-t border-slate-800 py-1">
        <div className="px-4 py-1 text-[10px] text-slate-500">
          ■ データのリセット（次のイベント準備）
        </div>
        <div className="space-y-2 px-4 py-2">
          <button
            onClick={() => resetData("attendance")}
            className="w-full rounded-lg bg-slate-800 py-2.5 text-xs font-bold text-slate-200"
          >
            受付状況だけリセット（来場・集金を全部クリア／参加者は残す）
          </button>
          <div className="flex gap-2">
            <button
              onClick={() => resetData("attendees")}
              className="flex-1 rounded-lg bg-rose-500/15 py-2.5 text-xs font-bold text-rose-300"
            >
              参加者を全削除
            </button>
            <button
              onClick={() => resetData("expenses")}
              className="flex-1 rounded-lg bg-rose-500/15 py-2.5 text-xs font-bold text-rose-300"
            >
              費用を全削除
            </button>
          </div>
        </div>
        <p className="px-4 pb-4 text-[10px] text-slate-600">
          ⚠️ 削除は取り消せません。心配な場合は先に「💾 保存」でバックアップを取ってから実行してください。
          まったく新しい会でゼロから始めるなら「＋新しいイベント」がおすすめです。
        </p>
      </section>

      {/* 役職 編集モーダル（会費・ご支援金・グループを1画面で） */}
      {rankDraft && (
        <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 sm:items-center">
          <div className="w-full max-w-md rounded-t-2xl bg-slate-900 p-4 sm:rounded-2xl">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-bold">役職の金額を編集</h2>
              <button onClick={() => setRankDraft(null)} className="px-2 text-slate-400">
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <label className="block">
                <span className="text-[10px] text-slate-400">役職名</span>
                <input
                  value={rankDraft.name}
                  onChange={(e) => setRankDraft({ ...rankDraft, name: e.target.value })}
                  className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                />
              </label>

              <div className="flex items-end gap-2">
                <label className="flex-1">
                  <span className="text-[10px] text-slate-400">会費（円）</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    value={rankDraft.fee}
                    onChange={(e) =>
                      setRankDraft({ ...rankDraft, fee: Math.max(0, Number(e.target.value) || 0) })
                    }
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  />
                </label>
                <label className="flex-1">
                  <span className="text-[10px] text-slate-400">ご支援金（円）</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    value={rankDraft.support}
                    onChange={(e) =>
                      setRankDraft({
                        ...rankDraft,
                        support: Math.max(0, Number(e.target.value) || 0),
                      })
                    }
                    className="w-full rounded-lg bg-slate-800 px-2 py-2 text-sm outline-none"
                  />
                </label>
                <div className="flex-1">
                  <span className="text-[10px] text-slate-400">負担額（自動）</span>
                  <div className="rounded-lg bg-slate-800/50 px-2 py-2 text-sm font-bold tabular-nums">
                    {yen(rankDraft.fee + rankDraft.support)}円
                  </div>
                </div>
              </div>

              <label className="block">
                <span className="text-[10px] text-slate-400">返金グループ</span>
                <div className="mt-1 flex gap-2">
                  {(["flat", "exec"] as const).map((g) => (
                    <button
                      key={g}
                      onClick={() => setRankDraft({ ...rankDraft, grp: g })}
                      className={`flex-1 rounded-lg py-2 text-xs font-bold ${
                        rankDraft.grp === g
                          ? g === "flat"
                            ? "bg-sky-500 text-white"
                            : "bg-purple-500 text-white"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {g === "flat" ? "一般（一律返金）" : "役職者（按分返金）"}
                    </button>
                  ))}
                </div>
              </label>

              <div className="flex flex-col gap-2 pt-1">
                <button
                  onClick={() => saveRank(true)}
                  disabled={busy}
                  className="w-full rounded-lg bg-amber-500 py-2.5 text-sm font-bold text-slate-900 disabled:opacity-50"
                >
                  {busy ? "保存中…" : "保存して参加者の金額にも反映"}
                </button>
                <button
                  onClick={() => saveRank(false)}
                  disabled={busy}
                  className="w-full rounded-lg bg-slate-800 py-2 text-xs font-bold text-slate-300 disabled:opacity-50"
                >
                  テーブルのみ保存（参加者は変えない）
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
