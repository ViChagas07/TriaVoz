import type { Metadata } from "next";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { ArrowRight, Filter, PhoneCall, ShieldAlert } from "lucide-react";
import { Card, PageHeader } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import { formatDateTime, formatDuration, formatMoney } from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { CallList, ClinicSettings } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("calls");
  return { title: t("title") };
}

const STATUSES = ["in_progress", "completed", "transferred", "failed", "rejected"] as const;

function one(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function pageHref(params: { status?: string; day?: string; cursor?: string }): string {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.day) search.set("day", params.day);
  if (params.cursor) search.set("cursor", params.cursor);
  const query = search.toString();
  return query ? `/chamadas?${query}` : "/chamadas";
}

export default async function CallsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const t = await getTranslations("calls");
  const statusT = await getTranslations("status");
  const locale = await getLocale();
  const params = await searchParams;
  const status = one(params.status);
  const day = one(params.day);
  const cursor = one(params.cursor);
  const settings = await serverApi<ClinicSettings>("/settings/clinic");

  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (day) query.set("day", day);
  if (cursor) query.set("cursor", cursor);
  query.set("limit", "25");
  const calls = await serverApi<CallList>(`/calls?${query.toString()}`);

  return (
    <div className="space-y-5">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <Card className="p-4">
        <form action="/chamadas" method="get" className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1 text-xs">
            <span className="flex items-center gap-1.5 font-medium text-muted">
              <Filter aria-hidden className="size-3.5" />
              {t("status")}
            </span>
            <select
              name="status"
              defaultValue={status ?? ""}
              className="min-w-40 rounded-lg border border-border bg-background px-3 py-2 text-sm"
            >
              <option value="">{t("allStatuses")}</option>
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {statusT(value)}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-xs">
            <span className="font-medium text-muted">{t("day")}</span>
            <input
              type="date"
              name="day"
              defaultValue={day ?? ""}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-contrast"
          >
            {t("filters")}
          </button>
          {(status || day) && (
            <Link href="/chamadas" className="px-2 py-2 text-xs text-muted hover:text-text">
              {t("allStatuses")}
            </Link>
          )}
        </form>
      </Card>

      {calls.items.length === 0 ? (
        <EmptyState
          title={t("empty")}
          body={t("auditNote")}
          icon={<PhoneCall aria-hidden className="size-5" />}
        />
      ) : (
        <>
          <div className="hidden overflow-hidden rounded-2xl border border-border bg-surface md:block">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2/60 text-xs text-muted">
                <tr>
                  <th className="px-4 py-2.5 font-medium">{t("caller")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("started")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("status")}</th>
                  <th className="px-4 py-2.5 text-right font-medium">{t("duration")}</th>
                  <th className="px-4 py-2.5 text-right font-medium">{t("cost")}</th>
                  <th className="px-4 py-2.5 text-right font-medium" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {calls.items.map((call) => (
                  <tr key={call.id} className="transition-colors hover:bg-surface-2/50">
                    <td className="px-4 py-3">
                      <Link href={`/chamadas/${call.id}`} className="font-medium hover:text-primary-strong">
                        {call.caller_number ?? t("unknownCaller")}
                      </Link>
                      <p className="text-[0.68rem] text-muted">
                        {call.channel === "web" ? t("channelWeb") : t("channelPhone")}
                        {call.needs_review && (
                          <span className="ml-2 inline-flex items-center gap-1 text-st-pending">
                            <ShieldAlert aria-hidden className="size-3" />
                            {t("needsReview")}
                          </span>
                        )}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted">
                      {formatDateTime(call.started_at, locale, settings.timezone)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={call.status} />
                    </td>
                    <td className="px-4 py-3 text-right text-xs tabular-nums">
                      {formatDuration(call.duration_seconds)}
                    </td>
                    <td className="px-4 py-3 text-right text-xs tabular-nums">
                      {formatMoney(call.cost_cents, locale)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/chamadas/${call.id}`}
                        aria-label={`${t("view")} ${call.caller_number ?? call.id}`}
                        className="inline-grid size-7 place-items-center rounded-full border border-border text-muted hover:text-primary-strong"
                      >
                        <ArrowRight aria-hidden className="size-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="space-y-2 md:hidden">
            {calls.items.map((call) => (
              <li key={call.id}>
                <Link
                  href={`/chamadas/${call.id}`}
                  className="block rounded-2xl border border-border bg-surface p-4"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium">{call.caller_number ?? t("unknownCaller")}</p>
                    <StatusPill status={call.status} />
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {formatDateTime(call.started_at, locale, settings.timezone)} ·{" "}
                    {formatDuration(call.duration_seconds)} · {formatMoney(call.cost_cents, locale)}
                  </p>
                  {call.needs_review && (
                    <p className="mt-2 inline-flex items-center gap-1 text-[0.68rem] text-st-pending">
                      <ShieldAlert aria-hidden className="size-3" />
                      {t("needsReview")}
                    </p>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}

      {calls.next_cursor && (
        <div className="flex justify-center">
          <Link
            href={pageHref({ status, day, cursor: calls.next_cursor })}
            className="rounded-full border border-border bg-surface px-4 py-2 text-xs font-medium hover:border-primary/40"
          >
            {t("loadMore")}
          </Link>
        </div>
      )}
    </div>
  );
}
