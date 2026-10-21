"use client";

import { Wifi, WifiOff } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { StatusPill } from "@/components/StatusPill";
import { formatDuration, formatTime } from "@/lib/format";
import type { Call } from "@/lib/types";

type Frame = { type?: string; at?: string; data?: { call_id?: string } };

const EVENT_LABEL: Record<string, string> = {
  "call.started": "event_call_started",
  "call.ended": "event_call_ended",
  "request.created": "event_request_created",
  "request.updated": "event_request_updated",
  "request.spam": "event_request_spam",
  "appointment.created": "event_appointment_created",
  "appointment.moved": "event_appointment_moved",
  "appointment.canceled": "event_appointment_canceled",
};

export function ActivityFeed({
  initial,
  timezone,
  locale,
}: {
  initial: Call[];
  timezone?: string;
  locale: string;
}) {
  const t = useTranslations("dashboard");
  const router = useRouter();
  const [online, setOnline] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<number | null>(null);

  useEffect(() => {
    const source = new EventSource("/api/v1/events/stream");
    const onUpdate = (event: MessageEvent<string>) => {
      try {
        const frame = JSON.parse(event.data) as Frame;
        const key = frame.type ? EVENT_LABEL[frame.type] : undefined;
        if (key) setToast(t(key as "event_call_started"));
        router.refresh();
        if (toastTimer.current) window.clearTimeout(toastTimer.current);
        toastTimer.current = window.setTimeout(() => setToast(null), 5000);
      } catch {
        /* heartbeat or malformed frame */
      }
    };
    source.addEventListener("update", onUpdate as EventListener);
    source.onopen = () => setOnline(true);
    source.onerror = () => setOnline(false);
    return () => {
      source.removeEventListener("update", onUpdate as EventListener);
      source.close();
      if (toastTimer.current) window.clearTimeout(toastTimer.current);
    };
  }, [router, t]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs text-muted">
          {online ? (
            <Wifi aria-hidden className="size-3.5 text-st-done" />
          ) : (
            <WifiOff aria-hidden className="size-3.5 text-st-pending" />
          )}
          {online ? t("live") : t("offline")}
        </p>
        <span className="text-[0.68rem] text-muted">{t("activityHint")}</span>
      </div>

      {toast && (
        <p
          role="status"
          aria-live="polite"
          className="mt-3 rounded-lg border border-primary/25 bg-primary/10 px-3 py-2 text-xs font-medium text-primary-strong"
        >
          {toast}
        </p>
      )}

      <ul className="mt-3 divide-y divide-border">
        {initial.length === 0 && <li className="py-6 text-center text-xs text-muted">{t("emptyActivity")}</li>}
        {initial.map((call) => (
          <li key={call.id} className="flex items-center gap-3 py-2.5">
            <span className="w-12 shrink-0 text-[0.68rem] tabular-nums text-muted">
              {formatTime(call.started_at, locale, timezone)}
            </span>
            <div className="min-w-0 flex-1">
              <Link
                href={`/chamadas/${call.id}`}
                className="truncate text-sm font-medium hover:text-primary-strong"
              >
                {call.caller_number ?? "—"}
              </Link>
              <p className="truncate text-[0.68rem] text-muted">
                {call.duration_seconds ? formatDuration(call.duration_seconds) : t("live")} ·{" "}
                {call.channel}
              </p>
            </div>
            <StatusPill status={call.status} />
          </li>
        ))}
      </ul>
    </div>
  );
}
