"use client";

import { AlertTriangle, Ban, CheckCircle2, Clock, Loader2, ShieldAlert, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { clsx } from "clsx";

const STYLES: Record<string, string> = {
  urgent: "border-st-urgent/35 bg-st-urgent/10 text-st-urgent",
  pending: "border-st-pending/35 bg-st-pending/10 text-st-pending",
  in_progress: "border-st-progress/35 bg-st-progress/10 text-st-progress",
  done: "border-st-done/35 bg-st-done/10 text-st-done",
  completed: "border-st-done/35 bg-st-done/10 text-st-done",
  transferred: "border-st-progress/35 bg-st-progress/10 text-st-progress",
  booked: "border-st-done/35 bg-st-done/10 text-st-done",
  cancelled: "border-st-cancelled/35 bg-st-cancelled/10 text-st-cancelled",
  failed: "border-st-urgent/35 bg-st-urgent/10 text-st-urgent",
  rejected: "border-st-urgent/35 bg-st-urgent/10 text-st-urgent",
  spam: "border-st-spam/35 bg-st-spam/10 text-st-spam",
  active: "border-st-done/35 bg-st-done/10 text-st-done",
  inactive: "border-st-cancelled/35 bg-st-cancelled/10 text-st-cancelled",
  draft: "border-st-pending/35 bg-st-pending/10 text-st-pending",
  published: "border-st-done/35 bg-st-done/10 text-st-done",
  superseded: "border-border bg-surface-2 text-muted",
  normal: "border-border bg-surface-2 text-muted",
  low: "border-border bg-surface-2 text-muted",
};

const ICONS: Record<string, typeof Clock> = {
  urgent: AlertTriangle,
  pending: Clock,
  in_progress: Loader2,
  done: CheckCircle2,
  completed: CheckCircle2,
  transferred: Loader2,
  booked: CheckCircle2,
  cancelled: Ban,
  failed: XCircle,
  rejected: XCircle,
  spam: ShieldAlert,
  active: CheckCircle2,
  inactive: Ban,
  draft: Clock,
  published: CheckCircle2,
  superseded: Clock,
  normal: Clock,
  low: Clock,
};

const KNOWN = new Set(Object.keys(STYLES));

export function StatusPill({ status, className }: { status: string; className?: string }) {
  const t = useTranslations("status");
  const Icon = ICONS[status] ?? Clock;
  const label = KNOWN.has(status) ? t(status as "pending") : status;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        STYLES[status] ?? "border-border bg-surface-2 text-muted",
        className,
      )}
    >
      <Icon aria-hidden className="size-3.5" />
      {label}
    </span>
  );
}
