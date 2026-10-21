"use client";

import {
  CalendarClock,
  Check,
  Phone,
  ShieldAlert,
  UserPlus,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { RequestDetail, ServiceRequest, TeamUser, User } from "@/lib/types";

export function RequestPanel({
  detail,
  team,
  me,
  timezone,
  closeHref,
}: {
  detail: RequestDetail;
  team: TeamUser[];
  me: User | null;
  timezone: string;
  closeHref: string;
}) {
  const t = useTranslations("appointments");
  const errors = useTranslations("errors");
  const router = useRouter();
  const locale = useLocale();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const [status, setStatus] = useState(detail.status);
  const [assignedName, setAssignedName] = useState(detail.assigned_to_name);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmSpam, setConfirmSpam] = useState(false);
  const [assignTo, setAssignTo] = useState(me?.id ?? "");

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") router.push(closeHref);
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [closeHref, router]);

  async function run(
    label: string,
    path: string,
    init: RequestInit,
    onSuccess: (value: ServiceRequest) => void,
  ) {
    setBusy(label);
    setError(null);
    try {
      const updated = await api<ServiceRequest>(path, init);
      onSuccess(updated);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 403 ? errors("forbidden") : t("errorAction"));
    } finally {
      setBusy(null);
    }
  }

  function assign() {
    if (!assignTo) return;
    void run(
      "assign",
      `/requests/${detail.id}/assign`,
      { method: "POST", body: JSON.stringify({ user_id: assignTo }) },
      (updated) => {
        setAssignedName(updated.assigned_to_name);
      },
    );
  }

  function complete() {
    void run("complete", `/requests/${detail.id}/complete`, { method: "POST" }, (updated) => {
      setStatus(updated.status);
    });
  }

  function markSpam() {
    if (!confirmSpam) {
      setConfirmSpam(true);
      return;
    }
    void run(
      "spam",
      `/requests/${detail.id}/mark-spam`,
      { method: "POST", body: JSON.stringify({ expires_in_days: 7 }) },
      (updated) => {
        setStatus(updated.status);
        setConfirmSpam(false);
      },
    );
  }

  const closed = status === "done" || status === "cancelled" || status === "spam";

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation">
      <button
        type="button"
        aria-label={t("close")}
        onClick={() => router.push(closeHref)}
        className="absolute inset-0 bg-black/30 backdrop-blur-[1px]"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="request-panel-title"
        className="panel-in relative z-10 flex h-full w-full max-w-md flex-col overflow-hidden border-l border-border bg-surface shadow-2xl"
      >
        <div className="flex items-start justify-between gap-3 border-b border-border p-5">
          <div className="min-w-0">
            <p className="text-[0.68rem] font-medium uppercase tracking-[0.14em] text-muted">
              {t("details")}
            </p>
            <h2 id="request-panel-title" className="mt-1 text-lg font-semibold leading-snug">
              {detail.title}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <StatusPill status={status} />
              {detail.needs_review && (
                <span className="inline-flex items-center gap-1 rounded-full border border-st-pending/35 bg-st-pending/10 px-2 py-0.5 text-[0.62rem] font-medium text-st-pending">
                  <ShieldAlert aria-hidden className="size-3" />
                  {t("needsReview")}
                </span>
              )}
            </div>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={() => router.push(closeHref)}
            className="grid size-8 shrink-0 place-items-center rounded-full border border-border text-muted hover:text-text"
            aria-label={t("close")}
          >
            <X aria-hidden className="size-4" />
          </button>
        </div>

        <div className="transcript-scroll flex-1 space-y-5 overflow-y-auto p-5">
          {detail.description && (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted">{detail.description}</p>
          )}

          <dl className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-xl bg-surface-2/70 p-3">
              <dt className="text-muted">{t("customer")}</dt>
              <dd className="mt-0.5 truncate font-medium">{detail.patient_name ?? t("unknownPatient")}</dd>
            </div>
            <div className="rounded-xl bg-surface-2/70 p-3">
              <dt className="text-muted">{t("phone")}</dt>
              <dd className="mt-0.5 truncate font-medium">{detail.patient_phone ?? t("noPhone")}</dd>
            </div>
            <div className="rounded-xl bg-surface-2/70 p-3">
              <dt className="text-muted">{t("created")}</dt>
              <dd className="mt-0.5 font-medium">{formatDateTime(detail.created_at, locale, timezone)}</dd>
            </div>
            <div className="rounded-xl bg-surface-2/70 p-3">
              <dt className="text-muted">{t("updated")}</dt>
              <dd className="mt-0.5 font-medium">{formatDateTime(detail.updated_at, locale, timezone)}</dd>
            </div>
          </dl>

          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">{t("timeline")}</h3>
            {detail.timeline.length === 0 ? (
              <p className="mt-2 text-xs text-muted">{t("noTimeline")}</p>
            ) : (
              <ol className="mt-3 space-y-3">
                {detail.timeline.map((event) => (
                  <li key={event.id} className="flex gap-2.5">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                    <div>
                      <p className="text-xs font-medium">{event.event_type}</p>
                      {event.note && <p className="text-xs text-muted">{event.note}</p>}
                      <p className="text-[0.62rem] text-muted">
                        {formatDateTime(event.created_at, locale, timezone)}
                        {event.user_name ? ` · ${event.user_name}` : ""}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {detail.suspicion_flags.length > 0 && (
            <section className="rounded-xl border border-st-pending/30 bg-st-pending/10 p-3">
              <h3 className="flex items-center gap-1.5 text-xs font-medium text-st-pending">
                <ShieldAlert aria-hidden className="size-3.5" />
                {t("suspicion")}
              </h3>
              <ul className="mt-1.5 flex flex-wrap gap-1.5">
                {detail.suspicion_flags.map((flag) => (
                  <li key={flag} className="rounded-full bg-surface px-2 py-0.5 text-[0.62rem] text-muted">
                    {flag.replaceAll("_", " ")}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {assignedName && (
            <p className="text-xs text-muted">
              <span className="font-medium text-text">{assignedName}</span> · {t("assign")}
            </p>
          )}

          {error && (
            <p role="alert" className="rounded-lg border border-st-urgent/30 bg-st-urgent/10 px-3 py-2 text-xs text-st-urgent">
              {error}
            </p>
          )}
        </div>

        <div className="border-t border-border p-4">
          {confirmSpam && (
            <div className="mb-3 rounded-lg border border-st-urgent/30 bg-st-urgent/10 p-3 text-xs">
              <p className="font-medium text-st-urgent">{t("markPrank")}?</p>
              <p className="mt-1 text-muted">{t("prankHint")}</p>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={markSpam}
                  disabled={busy !== null}
                  className="rounded-full bg-st-urgent px-3 py-1.5 font-semibold text-white"
                >
                  {busy === "spam" ? t("markingPrank") : t("confirm")}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmSpam(false)}
                  className="rounded-full border border-border px-3 py-1.5"
                >
                  {t("close")}
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            {detail.patient_phone && (
              <a
                href={`tel:${detail.patient_phone}`}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium"
              >
                <Phone aria-hidden className="size-3.5" />
                {t("callBack")}
              </a>
            )}
            {detail.call_id && (
              <a
                href={`/chamadas/${detail.call_id}`}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium"
              >
                <CalendarClock aria-hidden className="size-3.5" />
                {t("call")}
              </a>
            )}
            {!closed && (
              <>
                {!assignedName && (
                  <div className="col-span-2 flex gap-2">
                    {team.length > 0 && (
                      <select
                        value={assignTo}
                        onChange={(event) => setAssignTo(event.target.value)}
                        aria-label={t("assign")}
                        className="min-w-0 flex-1 rounded-lg border border-border bg-background px-2 py-1.5 text-xs"
                      >
                        <option value="">{t("select")}</option>
                        {team.map((member) => (
                          <option key={member.id} value={member.id}>
                            {member.full_name}
                          </option>
                        ))}
                      </select>
                    )}
                    <button
                      type="button"
                      onClick={assign}
                      disabled={busy !== null || !assignTo}
                      className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium disabled:opacity-60"
                    >
                      <UserPlus aria-hidden className="size-3.5" />
                      {busy === "assign" ? t("assigning") : t("assign")}
                    </button>
                  </div>
                )}
                <button
                  type="button"
                  onClick={complete}
                  disabled={busy !== null}
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-contrast disabled:opacity-60"
                >
                  <Check aria-hidden className="size-3.5" />
                  {busy === "complete" ? t("completing") : t("complete")}
                </button>
                {!confirmSpam && (
                  <button
                    type="button"
                    onClick={markSpam}
                    disabled={busy !== null}
                    className={clsx(
                      "col-span-2 inline-flex items-center justify-center gap-1.5 rounded-lg border border-st-urgent/30 px-3 py-2 text-xs font-medium text-st-urgent",
                      busy === "spam" && "opacity-60",
                    )}
                  >
                    <ShieldAlert aria-hidden className="size-3.5" />
                    {busy === "spam" ? t("markingPrank") : t("markPrank")}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
