import type { Metadata } from "next";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import {
  ArrowRight,
  Ban,
  CalendarDays,
  Clock3,
  Gauge,
  PhoneCall,
  ShieldAlert,
  ShieldCheck,
  Timer,
  Wallet,
  Wrench,
} from "lucide-react";
import { ActivityFeed } from "@/components/ActivityFeed";
import { Card, PageHeader } from "@/components/Card";
import { CostBars, LatencyBars } from "@/components/Charts";
import { EmptyState } from "@/components/EmptyState";
import { ScopedMessages } from "@/components/ScopedMessages";
import {
  addDays,
  formatMoney,
  formatNumber,
  formatPercent,
  formatTime,
  formatWeekdayShort,
  isoDay,
  todayInZone,
} from "@/lib/format";
import { serverApi } from "@/lib/server-api";
import type { Appointment, Call, CallList, ClinicSettings, Dashboard } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("dashboard");
  return { title: t("title"), description: t("subtitle") };
}

export default async function DashboardPage() {
  const t = await getTranslations("dashboard");
  const locale = await getLocale();
  const settings = await serverApi<ClinicSettings>("/settings/clinic");
  const today = todayInZone(settings.timezone);
  const [dashboard, agenda, recent] = await Promise.all([
    serverApi<Dashboard>("/dashboard"),
    serverApi<Appointment[]>(
      `/agenda?date_from=${today}&date_to=${isoDay(addDays(new Date(), 1), settings.timezone)}`,
    ),
    serverApi<CallList>(`/calls?day=${today}&limit=8`),
  ]);

  const days = Array.from({ length: 7 }, (_, index) => {
    const date = addDays(new Date(), index - 6);
    return { day: isoDay(date, settings.timezone), date };
  });
  const dailyCalls = await Promise.all(
    days.map(async (entry) => {
      try {
        const page = await serverApi<CallList>(`/calls?day=${entry.day}&limit=100`);
        return page.items.reduce((sum, call) => sum + call.cost_cents, 0);
      } catch {
        return 0;
      }
    }),
  );

  const stages = (
    [
      ["end_of_utterance", "stage_end_of_utterance"],
      ["llm_ttft", "stage_llm"],
      ["tts_ttfb", "stage_tts"],
      ["time_to_first_audio", "stage_total"],
    ] as const
  ).map(([key, label]) => ({
    key,
    label: t(label as "stage_end_of_utterance"),
    p50: dashboard.latency_p50_ms[key] ?? 0,
    p95: dashboard.latency_p95_ms[key] ?? 0,
  }));

  const kpis = [
    {
      label: t("kpiPending"),
      value: formatNumber(dashboard.pending_requests, locale),
      icon: Clock3,
      href: "/agendamentos?tab=pending",
    },
    {
      label: t("kpiCalls"),
      value: formatNumber(dashboard.calls_today, locale),
      icon: PhoneCall,
      href: "/chamadas",
    },
    {
      label: t("kpiHandoff"),
      value: formatPercent(dashboard.handoff_rate, locale),
      icon: ShieldAlert,
      href: "/chamadas?status=transferred",
    },
    {
      label: t("kpiCost"),
      value: formatMoney(dashboard.cost_today_cents, locale),
      icon: Wallet,
      href: "/chamadas",
    },
  ];

  const quality = [
    {
      label: t("kpiAvgDuration"),
      value: `${formatNumber(Math.round(dashboard.avg_duration_seconds), locale)} ${t("secondsShort")}`,
      icon: Timer,
    },
    {
      label: t("kpiCostPerCall"),
      value: formatMoney(dashboard.cost_per_call_cents, locale),
      icon: Gauge,
    },
    {
      label: t("kpiToolErrors"),
      value: formatNumber(dashboard.tool_errors_today, locale),
      icon: Wrench,
    },
    {
      label: t("kpiSlotTaken"),
      value: `${formatNumber(dashboard.slot_taken_today, locale)} · ${formatPercent(
        dashboard.slot_taken_rate,
        locale,
      )}`,
      icon: Ban,
    },
    {
      label: t("kpiGatekeeper"),
      value: formatNumber(dashboard.gatekeeper_blocks_today, locale),
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <>
            <Link
              href="/chamadas"
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-xs font-medium"
            >
              {t("quickCalls")}
              <ArrowRight aria-hidden className="size-3.5" />
            </Link>
            <Link
              href="/agendamentos"
              className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast"
            >
              {t("quickAppointments")}
            </Link>
          </>
        }
      />

      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Link
              key={kpi.label}
              href={kpi.href}
              className="rounded-2xl border border-border bg-surface p-4 transition-colors hover:border-primary/35"
            >
              <span className="flex items-center justify-between text-xs text-muted">
                {kpi.label}
                <Icon aria-hidden className="size-4 text-primary-strong" />
              </span>
              <span className="mt-2 block text-2xl font-semibold tabular-nums tracking-tight">
                {kpi.value}
              </span>
            </Link>
          );
        })}
      </section>

      <section>
        <div className="mb-2 flex items-baseline justify-between gap-3">
          <h2 className="text-sm font-semibold">{t("qualityTitle")}</h2>
          <span className="text-[0.68rem] text-muted">{t("qualityHint")}</span>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
          {quality.map((metric) => {
            const Icon = metric.icon;
            return (
              <div
                key={metric.label}
                className="rounded-2xl border border-border bg-surface p-3.5"
              >
                <span className="flex items-center justify-between gap-2 text-[0.68rem] text-muted">
                  <span className="truncate">{metric.label}</span>
                  <Icon aria-hidden className="size-4 shrink-0 text-primary-strong" />
                </span>
                <span className="mt-1.5 block text-lg font-semibold tabular-nums">
                  {metric.value}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-semibold">{t("latencyTitle")}</h2>
            <span className="text-[0.68rem] text-muted">{t("latencyHint")}</span>
          </div>
          <div className="mt-4">
            {stages.every((stage) => stage.p50 === 0 && stage.p95 === 0) ? (
              <p className="py-8 text-center text-xs text-muted">{t("noLatency")}</p>
            ) : (
              <LatencyBars stages={stages} />
            )}
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-semibold">{t("costTitle")}</h2>
            <span className="text-[0.68rem] text-muted">{t("costHint")}</span>
          </div>
          <div className="mt-4">
            <CostBars
              locale={locale}
              points={days.map((entry, index) => ({
                day: entry.day,
                label: formatWeekdayShort(entry.date, locale, settings.timezone),
                cents: dailyCalls[index] ?? 0,
              }))}
            />
          </div>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <Card className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">{t("todayTitle")}</h2>
              <p className="text-[0.68rem] text-muted">{t("todayHint")}</p>
            </div>
            <CalendarDays aria-hidden className="size-4 text-primary-strong" />
          </div>
          {agenda.length === 0 ? (
            <EmptyState className="mt-4 border-0 bg-transparent py-8" title={t("emptyAgenda")} />
          ) : (
            <ul className="mt-4 divide-y divide-border">
              {agenda.slice(0, 8).map((appointment) => (
                <li key={appointment.id} className="flex items-center gap-3 py-2.5">
                  <span className="w-14 shrink-0 text-xs font-medium tabular-nums text-primary-strong">
                    {formatTime(appointment.starts_at, locale, settings.timezone)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{appointment.customer_name}</p>
                    <p className="truncate text-[0.68rem] text-muted">
                      {appointment.service_name} · {appointment.professional_name}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">{t("activityTitle")}</h2>
          </div>
          <ScopedMessages namespaces={["dashboard", "status", "common"]} timeZone={settings.timezone}>
            <ActivityFeed
              initial={recent.items}
              timezone={settings.timezone}
              locale={locale}
            />
          </ScopedMessages>
        </Card>
      </section>
    </div>
  );
}
