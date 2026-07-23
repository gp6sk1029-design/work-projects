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

  // 役職の金額編集（会費・支援金をまとめて）
  async function editRank(r: Rank) {
    const feeIn = window.prompt(`「${r.name}」の会費（円）`, String(r.fee));
    if (feeIn === null) return;
    const supIn = window.prompt(`「${r.name}」のご支援金（円）`, String(r.support));
    if (supIn === null) return;
    const fee = Number(feeIn.replace(/[^0-9]/g, ""));
    const support = Number(supIn.replace(/[^0-9]/g, ""));
    if (!Number.isFinite(fee) || !Number.isFinite(support)) return alert("数字で入力してください");

    const apply = window.confirm(
      `会費テーブルを更新します。\n「${r.name}」の参加者の徴収額（${yen(fee + support)}円）にも反映しますか？\n（OK=参加者にも反映 / キャンセル=テーブルのみ）`
    );
    setBusy(true);
    try {
      const res = await fetch(`/api/ranks/${r.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fee, support, applyToAttendees: apply }),
      });
      const data = (await res.json()) as { rank?: Rank; error?: string };
      if (!res.ok || !data.rank) throw new Error(data.error ?? "保存に失敗しました");
      setRanks(ranks.map((x) => (x.id === r.id ? data.rank! : x)));
      if (apply) {
        // 参加者側も再取得
        const at = (await fetch("/api/attendees").then((x) => x.json())) as {
          attendees: Attendee[];
        };
        setAttendees(at.attendees);
      }
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
            <li key={ev.id}>
              <button
                onClick={() => activateEvent(ev)}
                className="flex w-full items-center gap-2 px-4 py-2.5 text-left active:bg-slate-900"
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
            </li>
          ))}
        </ul>
        <p className="px-4 py-4 text-center text-[10px] text-slate-600">
          イベントを切り替えても過去のデータは残ります。次回の歓送迎会は「＋新しいイベント」から。
        </p>
      </section>
    </div>
  );
}
