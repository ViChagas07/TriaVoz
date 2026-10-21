import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getLocale, getTranslations } from "next-intl/server";
import {
  ArrowLeft,
  CalendarCheck2,
  Clock3,
  FileText,
  Gauge,
  PhoneCall,
  ShieldAlert,
  Wrench,
} from "lucide-react";
import { Card, PageHeader } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import {
  addDays,
  formatDateTime,
  formatDuration,
  formatMoney,
  formatPercent,
  formatTime,
  isoDay,
} from "@/lib/format";
import { serverApi, ServerApiError } from "@/lib/server-api";
import type {
  Appointment,
  CallDetail,
  CallEvent,
  CallTurn,
  ClinicSettings,
} from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("calls");
  return { title: t("detailTitle") };
}

export default async function CallDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const t = await getTranslations("calls");
  const locale = await getLocale();
  const settings = await serverApi<ClinicSettings>("/settings/clinic");

  let call: CallDetail;
  let turns: CallTurn[];
  let events: CallEvent[];
  try {
    [call, turns, events] = await Promise.all([
      serverApi<CallDetail>(`/calls/${id}`),
      serverApi<CallTurn[]>(`/calls/${id}/turns`),
      serverApi<CallEvent[]>(`/calls/${id}/events`),
    ]);
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 404) notFound();
    throw error;
  }

  let appointment: Appointment | undefined;
  try {
    // An appointment made by the call can land on a later day; widen the window.
    const agenda = await serverApi<Appointment[]>(
      `/agenda?date_from=${isoDay(addDays(new Date(call.started_at), -1), settings.timezone)}&date_to=${isoDay(addDays(new Date(call.started_at), 2), settings.timezone)}`,
    );
    appointment = agenda.find((item) => item.call_id === call.id);
  } catch {
    appointment = undefined;
  }

  const latency: { key: string; p50: number; p95: number }[] = [];
  for (const [key, value] of Object.entries(call.latency_ms ?? {})) {
    if (typeof value === "number") {
      latency.push({ key, p50: value, p95: value });
      continue;
    }
    if (
      value &&
      typeof value === "object" &&
      typeof (value as { p50?: unknown }).p50 === "number"
    ) {
      const stats = value as { p50: number; p95?: number };
      latency.push({ key, p50: stats.p50, p95: stats.p95 ?? stats.p50 });
    }
  }
  const usage = Object.entries(call.usage ?? {}).filter(
    ([, value]) => typeof value === "number" || typeof value === "string",
  ) as [string, number | string][];
  const stageLabel: Record<string, string> = {
    stt: "STT",
    llm: "LLM",
    tts: "TTS",
    total: "Total",
  };
  const usageLabel = (key: string) =>
    key
      .replace(/^llm_/, "LLM ")
      .replace(/^stt_/, "STT ")
      .replace(/^tts_/, "TTS ")
      .replaceAll("_", " ")
      .replace(/^./, (letter) => letter.toUpperCase());

  return (
    <div className="space-y-5">
      <Link
        href="/chamadas"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-text"
      >
        <ArrowLeft aria-hidden className="size-3.5" />
        {t("back")}
      </Link>

      <PageHeader
        eyebrow={t("detailTitle")}
        title={call.caller_number ?? t("unknownCaller")}
        subtitle={`${formatDateTime(call.started_at, locale, settings.timezone)} · ${
          call.channel === "web" ? t("channelWeb") : t("channelPhone")
        }`}
        actions={
          <>
            <StatusPill status={call.status} />
            {call.needs_review && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-st-pending/35 bg-st-pending/10 px-2.5 py-1 text-xs font-medium text-st-pending">
                <ShieldAlert aria-hidden className="size-3.5" />
                {t("needsReview")}
              </span>
            )}
          </>
        }
      />

      <section className="grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <FileText aria-hidden className="size-4 text-primary-strong" />
              {t("summary")}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              {call.summary || t("noSummary")}
            </p>
            {call.end_reason && (
              <p className="mt-2 text-[0.68rem] text-muted">
                {call.end_reason} · {formatDuration(call.duration_seconds)}
              </p>
            )}
          </Card>

          <Card className="p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">{t("transcript")}</h2>
              <span className="text-[0.68rem] text-muted">{t("auditNote")}</span>
            </div>
            {turns.length === 0 ? (
              <EmptyState className="mt-4 border-0 bg-transparent py-8" title={t("noTranscript")} />
            ) : (
              <ol className="mt-4 space-y-3">
                {turns.map((turn) => {
                  if (turn.speaker === "tool") {
                    const isError = turn.tool_payload?.is_error === true;
                    return (
                      <li key={turn.id} className="flex items-start gap-2.5">
                        <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full border border-border bg-surface-2 text-muted">
                          <Wrench aria-hidden className="size-3.5" />
                        </span>
                        <div
                          className={`min-w-0 flex-1 rounded-xl border px-3 py-2 text-xs ${
                            isError
                              ? "border-st-urgent/25 bg-st-urgent/5"
                              : "border-st-done/25 bg-st-done/5"
                          }`}
                        >
                          <div className="flex flex-wrap items-center gap-2 font-medium">
                            <span>{turn.tool_name ?? t("tool")}</span>
                            <span className={isError ? "text-st-urgent" : "text-st-done"}>
                              {isError ? t("toolError") : t("toolOk")}
                            </span>
                            <span className="ml-auto text-[0.62rem] tabular-nums text-muted">
                              {formatTime(turn.started_at, locale, settings.timezone)}
                            </span>
                          </div>
                          {turn.tool_payload?.arguments ? (
                            <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap break-words text-[0.65rem] text-muted">
                              {JSON.stringify(turn.tool_payload.arguments, null, 2)}
                            </pre>
                          ) : null}
                        </div>
                      </li>
                    );
                  }
                  const patient = turn.speaker === "patient";
                  return (
                    <li
                      key={turn.id}
                      className={`flex ${patient ? "justify-start" : "justify-end"}`}
                    >
                      <div
                        className={`max-w-[86%] rounded-2xl px-3.5 py-2.5 text-sm ${
                          patient
                            ? "rounded-bl-md bg-surface-2 text-text"
                            : "rounded-br-md bg-primary text-primary-contrast"
                        }`}
                      >
                        <div className="mb-1 flex items-center gap-2 text-[0.62rem] font-semibold uppercase tracking-wider opacity-75">
                          <span>{patient ? t("speakerPatient") : t("speakerAgent")}</span>
                          <span className="tabular-nums">
                            {formatTime(turn.started_at, locale, settings.timezone)}
                          </span>
                          {turn.stt_confidence !== null && patient && (
                            <span>{formatPercent(turn.stt_confidence, locale)}</span>
                          )}
                        </div>
                        <p className="whitespace-pre-wrap break-words">{turn.content}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <Gauge aria-hidden className="size-4 text-primary-strong" />
              {t("metrics")}
            </h2>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-xl bg-surface-2/70 p-3">
                <dt className="text-muted">{t("duration")}</dt>
                <dd className="mt-0.5 text-sm font-medium">{formatDuration(call.duration_seconds)}</dd>
              </div>
              <div className="rounded-xl bg-surface-2/70 p-3">
                <dt className="text-muted">{t("cost")}</dt>
                <dd className="mt-0.5 text-sm font-medium">{formatMoney(call.cost_cents, locale)}</dd>
              </div>
            </dl>

            {latency.length > 0 && (
              <>
                <h3 className="mt-4 text-[0.68rem] font-medium uppercase tracking-wider text-muted">
                  {t("latency")}
                </h3>
                <dl className="mt-2 space-y-1.5 text-xs">
                  {latency.map((stage) => (
                    <div key={stage.key} className="flex items-center justify-between gap-2">
                      <dt className="text-muted">{stageLabel[stage.key] ?? usageLabel(stage.key)}</dt>
                      <dd className="tabular-nums">
                        {Math.round(stage.p50)} / {Math.round(stage.p95)} ms
                      </dd>
                    </div>
                  ))}
                </dl>
              </>
            )}

            {usage.length > 0 && (
              <>
                <h3 className="mt-4 text-[0.68rem] font-medium uppercase tracking-wider text-muted">
                  {t("usage")}
                </h3>
                <dl className="mt-2 space-y-1.5 text-xs">
                  {usage.slice(0, 12).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between gap-2">
                      <dt className="truncate text-muted">{usageLabel(key)}</dt>
                      <dd className="max-w-[55%] truncate text-right tabular-nums">
                        {typeof value === "number" ? value.toFixed(1) : value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </>
            )}

            {call.needs_review && (
              <p className="mt-4 rounded-lg border border-st-pending/30 bg-st-pending/10 px-3 py-2 text-[0.68rem] text-st-pending">
                {t("reviewHint")}
              </p>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <CalendarCheck2 aria-hidden className="size-4 text-primary-strong" />
              {t("appointment")}
            </h2>
            {appointment ? (
              <div className="mt-3 text-sm">
                <p className="font-medium">{appointment.service_name}</p>
                <p className="text-xs text-muted">{appointment.professional_name}</p>
                <p className="mt-2 flex items-center gap-1.5 text-xs text-muted">
                  <Clock3 aria-hidden className="size-3.5" />
                  {formatDateTime(appointment.starts_at, locale, settings.timezone)}
                </p>
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted">{t("noAppointment")}</p>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <PhoneCall aria-hidden className="size-4 text-primary-strong" />
              {t("events")}
            </h2>
            {events.length === 0 ? (
              <p className="mt-2 text-xs text-muted">{t("noEvents")}</p>
            ) : (
              <ol className="mt-3 space-y-2.5">
                {events.map((event) => (
                  <li key={event.id} className="flex gap-2 text-xs">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                    <div className="min-w-0">
                      <p className="font-medium">{event.event_type}</p>
                      <p className="text-[0.65rem] text-muted">
                        {formatDateTime(event.created_at, locale, settings.timezone)}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>
      </section>
    </div>
  );
}
