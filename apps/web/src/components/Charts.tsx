import { formatMoney } from "@/lib/format";

type CostPoint = { day: string; label: string; cents: number };

export function CostBars({ points, locale }: { points: CostPoint[]; locale: string }) {
  const max = Math.max(1, ...points.map((point) => point.cents));
  return (
    <div className="flex h-40 items-end gap-2" role="img" aria-label={points.map((point) => `${point.label}: ${formatMoney(point.cents, locale)}`).join(", ")}>
      {points.map((point) => (
        <div key={point.day} className="flex min-w-0 flex-1 flex-col items-center gap-1.5">
          <span className="text-[0.62rem] tabular-nums text-muted">
            {point.cents > 0 ? formatMoney(point.cents, locale) : "—"}
          </span>
          <div className="flex h-28 w-full items-end rounded-md bg-surface-2/70">
            <div
              className="w-full rounded-md bg-primary/75 transition-[height]"
              style={{ height: `${Math.max(4, (point.cents / max) * 100)}%` }}
            />
          </div>
          <span className="truncate text-[0.62rem] text-muted">{point.label}</span>
        </div>
      ))}
    </div>
  );
}

type Stage = { key: string; label: string; p50: number; p95: number };

export function LatencyBars({ stages }: { stages: Stage[] }) {
  const max = Math.max(1, ...stages.flatMap((stage) => [stage.p50, stage.p95]));
  return (
    <div className="space-y-3" role="img" aria-label={stages.map((stage) => `${stage.label}: p50 ${Math.round(stage.p50)} ms, p95 ${Math.round(stage.p95)} ms`).join("; ")}>
      {stages.map((stage) => (
        <div key={stage.key}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="font-medium">{stage.label}</span>
            <span className="tabular-nums text-muted">
              p50 {Math.round(stage.p50)} · p95 {Math.round(stage.p95)} ms
            </span>
          </div>
          <div className="space-y-1">
            <div className="h-1.5 rounded-full bg-surface-2">
              <div className="h-full rounded-full bg-primary" style={{ width: `${(stage.p50 / max) * 100}%` }} />
            </div>
            <div className="h-1 rounded-full bg-surface-2">
              <div className="h-full rounded-full bg-primary/35" style={{ width: `${(stage.p95 / max) * 100}%` }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
