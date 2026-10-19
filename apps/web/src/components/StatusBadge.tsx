import { AlertTriangle, Ban, CheckCircle2, Clock, Loader2, ShieldAlert } from "lucide-react";
import { getTranslations } from "next-intl/server";
import clsx from "clsx";

export type RequestStatus = "pending" | "in_progress" | "done" | "cancelled" | "spam" | "urgent";

const STYLES: Record<RequestStatus, { icon: typeof Clock; color: string }> = {
  urgent: { icon: AlertTriangle, color: "text-st-urgent border-st-urgent/40 bg-st-urgent/10" },
  pending: { icon: Clock, color: "text-st-pending border-st-pending/40 bg-st-pending/10" },
  in_progress: { icon: Loader2, color: "text-st-progress border-st-progress/40 bg-st-progress/10" },
  done: { icon: CheckCircle2, color: "text-st-done border-st-done/40 bg-st-done/10" },
  cancelled: { icon: Ban, color: "text-st-cancelled border-st-cancelled/40 bg-st-cancelled/10" },
  spam: { icon: ShieldAlert, color: "text-st-spam border-st-spam/40 bg-st-spam/10" },
};

/** Status is ALWAYS communicated by icon + text + color (never color alone: a11y / color blindness). */
export async function StatusBadge({ status }: { status: RequestStatus }) {
  const t = await getTranslations("status");
  const { icon: Icon, color } = STYLES[status];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        color,
      )}
    >
      <Icon aria-hidden className="size-3.5" />
      {t(status)}
    </span>
  );
}
