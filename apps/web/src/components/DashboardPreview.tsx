import { Check, ChevronRight } from "lucide-react";

type Props = {
  t: (key: string) => string;
};

/** Static, fictional preview of the clinic dashboard, rendered inside a browser frame
 * on the landing page. All data is hardcoded marketing copy, not live data. */
export function DashboardPreview({ t }: Props) {
  const stats = [
    { value: "28", label: t("previewStat1") },
    { value: "5", label: t("previewStat2") },
    { value: "7", label: t("previewStat3") },
  ];
  const events = [
    { label: t("previewEvent1"), time: "1 min" },
    { label: t("previewEvent2"), time: "2 min" },
    { label: t("previewEvent3"), time: "3 min" },
  ];
  const upcoming = [
    { name: "Maria Costa", time: "09:30", detail: "Consulta geral · Dra. Ana" },
    { name: "João Ribeiro", time: "10:10", detail: "Retorno · Dra. Helena Duarte" },
    { name: "Beatriz Almeida", time: "11:00", detail: "Exame · Dr. Rafael Lima" },
  ];

  return (
    <div className="overflow-hidden rounded-3xl border border-border bg-surface shadow-card">
      <div className="flex items-center gap-2 border-b border-border bg-surface-2/80 px-4 py-2.5">
        <span className="size-2.5 rounded-full bg-st-urgent/80" aria-hidden />
        <span className="size-2.5 rounded-full bg-st-pending/80" aria-hidden />
        <span className="size-2.5 rounded-full bg-st-done/80" aria-hidden />
        <span className="ml-3 truncate font-mono text-[0.65rem] text-muted">
          app.triavoice.local/painel
        </span>
      </div>

      <div className="grid gap-0 lg:grid-cols-[1.4fr_1fr]">
        <div className="p-5 sm:p-6">
          <p className="eyebrow">{t("previewLive")}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h3 className="display-title text-xl sm:text-2xl">{t("previewGreeting")}</h3>
            <span className="rounded-full bg-primary-soft px-2.5 py-0.5 font-mono text-[0.65rem] font-semibold text-primary-strong">
              {t("previewClinic")}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-2.5">
            {stats.map((stat) => (
              <div key={stat.label} className="rounded-xl border border-border bg-surface p-3">
                <p className="font-display text-2xl font-extrabold text-heading">{stat.value}</p>
                <p className="mt-0.5 font-mono text-[0.62rem] text-muted">{stat.label}</p>
              </div>
            ))}
          </div>

          <div className="mt-5 flex items-center justify-between gap-3">
            <p className="font-mono text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-muted">
              {t("previewRecent")}
            </p>
            <span className="inline-flex items-center gap-0.5 font-mono text-[0.65rem] font-semibold text-primary-strong">
              {t("previewViewAll")}
              <ChevronRight aria-hidden className="size-3" />
            </span>
          </div>
          <ul className="mt-1 divide-y divide-border">
            {events.map((event) => (
              <li key={event.label} className="flex items-center gap-2.5 py-2.5 text-sm">
                <span
                  aria-hidden
                  className="size-1.5 shrink-0 rounded-full bg-[color-mix(in_oklab,var(--grad-b)_70%,var(--grad-a))]"
                />
                <span className="min-w-0 flex-1 truncate">{event.label}</span>
                <span className="font-mono text-[0.62rem] text-muted">{event.time}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="border-t border-border bg-surface-2/60 p-5 sm:p-6 lg:border-l lg:border-t-0">
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-surface-2 p-1">
            <span className="rounded-md bg-primary px-2 py-1.5 text-center font-mono text-[0.65rem] font-semibold text-primary-contrast">
              {t("previewTabPanel")}
            </span>
            <span className="rounded-md px-2 py-1.5 text-center font-mono text-[0.65rem] font-semibold text-muted">
              {t("previewTabTranscript")}
            </span>
          </div>

          <p className="mt-5 font-mono text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-muted">
            {t("previewNext")}
          </p>
          <ul className="mt-1 divide-y divide-border">
            {upcoming.map((item) => (
              <li key={item.name} className="flex items-center gap-3 py-2.5">
                <span className="w-11 shrink-0 font-mono text-xs font-semibold text-primary-strong">
                  {item.time}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{item.name}</p>
                  <p className="truncate text-[0.65rem] text-muted">{item.detail}</p>
                </div>
                <Check aria-hidden className="size-3.5 shrink-0 text-st-done" />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
