import type { Metadata } from "next";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { CalendarDays, ListChecks } from "lucide-react";
import { Card, PageHeader } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ScopedMessages } from "@/components/ScopedMessages";
import { StatusPill } from "@/components/StatusPill";
import { RequestPanel } from "@/components/RequestPanel";
import { NewAppointmentDialog } from "@/components/NewAppointmentDialog";
import { getSession, serverApi, ServerApiError } from "@/lib/server-api";
import {
  addDays,
  formatDate,
  formatDateTime,
  formatDayLabel,
  formatTime,
  isoDay,
  todayInZone,
} from "@/lib/format";
import type {
  Appointment,
  ClinicSettings,
  Professional,
  RequestDetail,
  RequestList,
  Service,
  TeamUser,
} from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("appointments");
  return { title: t("title") };
}

type Tab = "agenda" | "pending" | "history";

const TYPE_KEYS: Record<string, "typeAppointment" | "typeExamPickup" | "typeMessage" | "typeCallback" | "typeOther"> = {
  appointment: "typeAppointment",
  exam_pickup: "typeExamPickup",
  message: "typeMessage",
  callback: "typeCallback",
  other: "typeOther",
};

const PRIORITY_KEYS: Record<string, "priorityUrgent" | "priorityNormal" | "priorityLow"> = {
  urgent: "priorityUrgent",
  normal: "priorityNormal",
  low: "priorityLow",
};

function one(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function tabsHref(tab: Tab, extra?: Record<string, string>): string {
  const params = new URLSearchParams({ tab, ...(extra ?? {}) });
  return `/agendamentos?${params.toString()}`;
}

export default async function AppointmentsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const t = await getTranslations("appointments");
  const locale = await getLocale();
  const params = await searchParams;
  const tab: Tab = params.tab === "pending" || params.tab === "history" ? params.tab : "agenda";
  const settings = await serverApi<ClinicSettings>("/settings/clinic");
  const today = todayInZone(settings.timezone);
  const session = await getSession();
  const isAdmin = session?.user.role === "admin";

  const [services, professionals] = await Promise.all([
    serverApi<Service[]>("/services"),
    serverApi<Professional[]>("/professionals"),
  ]);
  const team = isAdmin
    ? await serverApi<TeamUser[]>("/team").catch(() => [])
    : [];

  const requestId = one(params.request);
  let detail: RequestDetail | null = null;
  if (requestId) {
    try {
      detail = await serverApi<RequestDetail>(`/requests/${requestId}`);
    } catch (error) {
      if (!(error instanceof ServerApiError && error.status === 404)) throw error;
    }
  }

  const professionalFilter = one(params.professional);
  const dateFrom = one(params.date_from) ?? today;
  const dateTo = one(params.date_to) ?? isoDay(addDays(new Date(), 14), settings.timezone);
  const search = one(params.q) ?? "";
  const statusFilter = one(params.status);
  const typeFilter = one(params.type);
  const priorityFilter = one(params.priority);

  let agenda: Appointment[] = [];
  let pending: RequestList["items"] = [];
  let history: RequestList["items"] = [];
  if (tab === "agenda") {
    const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
    if (professionalFilter) query.set("professional_id", professionalFilter);
    agenda = await serverApi<Appointment[]>(`/agenda?${query.toString()}`);
  } else if (tab === "pending") {
    const base = new URLSearchParams({ limit: "50" });
    if (typeFilter) base.set("type", typeFilter);
    if (priorityFilter) base.set("priority", priorityFilter);
    if (search) base.set("search", search);
    const [pendingPage, progressPage] = await Promise.all([
      serverApi<RequestList>(`/requests?status=pending&${base.toString()}`),
      serverApi<RequestList>(`/requests?status=in_progress&${base.toString()}`),
    ]);
    pending = [...progressPage.items, ...pendingPage.items].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
  } else {
    const base = new URLSearchParams({ limit: "50" });
    if (typeFilter) base.set("type", typeFilter);
    if (priorityFilter) base.set("priority", priorityFilter);
    if (search) base.set("search", search);
    const pages = await Promise.all(
      (["done", "cancelled", "spam"] as const).map((status) =>
        serverApi<RequestList>(`/requests?status=${status}&${base.toString()}`),
      ),
    );
    history = pages
      .flatMap((page) => page.items)
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  }

  const dayGroups = new Map<string, Appointment[]>();
  for (const appointment of agenda) {
    const key = isoDay(new Date(appointment.starts_at), settings.timezone);
    const list = dayGroups.get(key) ?? [];
    list.push(appointment);
    dayGroups.set(key, list);
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <NewAppointmentDialog
            services={services.filter((service) => service.is_active)}
            professionals={professionals.filter((professional) => professional.is_active)}
            strings={{
              trigger: t("newAppointment"),
              title: t("newTitle"),
              hint: t("newHint"),
              service: t("serviceLabel"),
              professional: t("professionalLabel"),
              date: t("dateLabel"),
              name: t("nameLabel"),
              phone: t("phoneLabel"),
              create: t("create"),
              creating: t("creating"),
              cancel: t("close"),
              created: t("createdOk"),
              error: t("errorCreate"),
            }}
          />
        }
      />

      <nav className="flex gap-1 overflow-x-auto rounded-xl border border-border bg-surface p-1" aria-label={t("title")}>
        {(
          [
            ["agenda", t("tabsAgenda")],
            ["pending", t("tabsPending")],
            ["history", t("tabsHistory")],
          ] as const
        ).map(([key, label]) => (
          <Link
            key={key}
            href={tabsHref(key)}
            aria-current={tab === key ? "page" : undefined}
            className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
              tab === key
                ? "bg-primary/10 text-primary-strong"
                : "text-muted hover:bg-surface-2 hover:text-text"
            }`}
          >
            {label}
          </Link>
        ))}
      </nav>

      {tab === "agenda" && (
        <Card className="p-4">
          <form action="/agendamentos" method="get" className="flex flex-wrap items-end gap-3">
            <input type="hidden" name="tab" value="agenda" />
            <label className="grid gap-1 text-xs">
              <span className="font-medium text-muted">{t("dateFrom")}</span>
              <input
                type="date"
                name="date_from"
                defaultValue={dateFrom}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </label>
            <label className="grid gap-1 text-xs">
              <span className="font-medium text-muted">{t("dateTo")}</span>
              <input
                type="date"
                name="date_to"
                defaultValue={dateTo}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </label>
            <label className="grid gap-1 text-xs">
              <span className="font-medium text-muted">{t("professional")}</span>
              <select
                name="professional"
                defaultValue={professionalFilter ?? ""}
                className="min-w-48 rounded-lg border border-border bg-background px-3 py-2 text-sm"
              >
                <option value="">{t("allProfessionals")}</option>
                {professionals.map((professional) => (
                  <option key={professional.id} value={professional.id}>
                    {professional.name}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-contrast">
              {t("filters")}
            </button>
          </form>
        </Card>
      )}

      {tab !== "agenda" && (
        <Card className="p-4">
          <form action="/agendamentos" method="get" className="flex flex-wrap items-end gap-3">
            <input type="hidden" name="tab" value={tab} />
            <label className="grid min-w-52 flex-1 gap-1 text-xs">
              <span className="font-medium text-muted">{t("search")}</span>
              <input
                type="search"
                name="q"
                defaultValue={search}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </label>
            <label className="grid gap-1 text-xs">
              <span className="font-medium text-muted">{t("type")}</span>
              <select
                name="type"
                defaultValue={typeFilter ?? ""}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              >
                <option value="">{t("allTypes")}</option>
                {Object.entries(TYPE_KEYS).map(([value, key]) => (
                  <option key={value} value={value}>
                    {t(key)}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-xs">
              <span className="font-medium text-muted">{t("priority")}</span>
              <select
                name="priority"
                defaultValue={priorityFilter ?? ""}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              >
                <option value="">{t("allPriorities")}</option>
                {Object.entries(PRIORITY_KEYS).map(([value, key]) => (
                  <option key={value} value={value}>
                    {t(key)}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-contrast">
              {t("filters")}
            </button>
          </form>
        </Card>
      )}

      {tab === "agenda" && (
        <div className="space-y-4">
          {dayGroups.size === 0 ? (
            <EmptyState
              title={t("emptyAgenda")}
              icon={<CalendarDays aria-hidden className="size-5" />}
            />
          ) : (
            [...dayGroups.entries()].map(([day, items]) => (
              <Card key={day} className="overflow-hidden">
                <div className="flex items-center justify-between border-b border-border bg-surface-2/50 px-4 py-2.5">
                  <h2 className="text-sm font-semibold">
                    {formatDayLabel(`${day}T12:00:00`, locale, settings.timezone)}
                  </h2>
                  <span className="text-[0.68rem] text-muted">{items.length}</span>
                </div>
                <ul className="divide-y divide-border">
                  {items.map((appointment) => {
                    const byProfessional = new Map<string, Appointment[]>();
                    byProfessional.set(
                      appointment.professional_name,
                      (byProfessional.get(appointment.professional_name) ?? []).concat(appointment),
                    );
                    return (
                      <li key={appointment.id} className="flex items-center gap-3 px-4 py-3">
                        <span className="w-14 shrink-0 text-xs font-semibold tabular-nums text-primary-strong">
                          {formatTime(appointment.starts_at, locale, settings.timezone)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{appointment.customer_name}</p>
                          <p className="truncate text-[0.68rem] text-muted">
                            {appointment.service_name} · {appointment.professional_name}
                          </p>
                        </div>
                        <StatusPill status={appointment.status} />
                        {appointment.call_id && (
                          <Link
                            href={`/chamadas/${appointment.call_id}`}
                            className="text-[0.68rem] font-medium text-primary-strong hover:underline"
                          >
                            {t("call")}
                          </Link>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </Card>
            ))
          )}
        </div>
      )}

      {tab === "pending" && (
        <RequestTable
          items={pending}
          empty={t("emptyPending")}
          tab="pending"
          timezone={settings.timezone}
          locale={locale}
          t={t}
        />
      )}

      {tab === "history" && (
        <RequestTable
          items={history}
          empty={t("emptyHistory")}
          tab="history"
          timezone={settings.timezone}
          locale={locale}
          t={t}
        />
      )}

      {detail && (
        <ScopedMessages
          namespaces={["appointments", "common", "status", "errors"]}
          timeZone={settings.timezone}
        >
          <RequestPanel
            detail={detail}
            team={team}
            me={session?.user ?? null}
            timezone={settings.timezone}
            closeHref={tabsHref(tab, { ...(search ? { q: search } : {}) })}
          />
        </ScopedMessages>
      )}
    </div>
  );
}

function RequestTable({
  items,
  empty,
  tab,
  timezone,
  locale,
  t,
}: {
  items: RequestList["items"];
  empty: string;
  tab: Tab;
  timezone: string;
  locale: string;
  t: Awaited<ReturnType<typeof getTranslations<"appointments">>>;
}) {
  if (items.length === 0) {
    return <EmptyState title={empty} icon={<ListChecks aria-hidden className="size-5" />} />;
  }
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface">
      <ul className="divide-y divide-border">
        {items.map((request) => (
          <li key={request.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href={tabsHref(tab, { request: request.id })}
                  className="truncate text-sm font-medium hover:text-primary-strong"
                >
                  {request.title}
                </Link>
                {request.needs_review && (
                  <span className="rounded-full border border-st-pending/35 bg-st-pending/10 px-2 py-0.5 text-[0.62rem] font-medium text-st-pending">
                    {t("needsReview")}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-[0.68rem] text-muted">
                {request.patient_name ?? t("unknownPatient")} · {request.patient_phone ?? t("noPhone")} ·{" "}
                {formatDateTime(request.created_at, locale, timezone)}
              </p>
            </div>
            <span className="text-[0.68rem] text-muted">
              {TYPE_KEYS[request.type] ? t(TYPE_KEYS[request.type]!) : request.type}
            </span>
            <StatusPill status={request.status} />
            <Link
              href={tabsHref(tab, { request: request.id })}
              className="rounded-full border border-border px-2.5 py-1 text-[0.68rem] font-medium"
            >
              {t("details")}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
