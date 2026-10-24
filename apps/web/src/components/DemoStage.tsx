"use client";

import {
  AlertTriangle,
  ArrowRight,
  Check,
  Clock3,
  Loader2,
  Mic,
  PhoneOff,
  Radio,
  ShieldAlert,
  Volume2,
  Wrench,
  X,
} from "lucide-react";
import {
  Room,
  RoomEvent,
  Track,
  type Participant,
  type RemoteTrack,
  type TranscriptionSegment,
} from "livekit-client";
import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { clsx } from "clsx";
import { VoiceOrb, type OrbState } from "@/components/VoiceOrb";
import { createDemoRoom } from "@/lib/demo-room";
import { api, ApiError } from "@/lib/api";
import { formatDateTime, formatDuration } from "@/lib/format";
import type { VoiceSession } from "@/lib/types";

type Phase = "idle" | "requesting" | "connecting" | "live" | "ended" | "fallback" | "error";
type ErrorKind = "mic" | "network" | "session";
type ToolEvent = { id: string; name: string; ok: boolean; startsAt?: string; at: number };
type Caption = { id: string; speaker: "you" | "agent"; text: string; at: number };

type PreviewPhase = string;

const FALLBACK_LABEL: Record<string, string> = {
  budget: "budget",
  rate_limited: "rateLimited",
  cost_budget: "budget",
  cost_breaker: "budget",
  minute_budget: "budget",
  kill_switch: "killSwitch",
  after_hours: "afterHours",
  blocked: "blocked",
  hidden_number: "blocked",
  concurrency: "concurrency",
};

const TOOL_KEYS = new Set([
  "list_services",
  "list_available_slots",
  "book_appointment",
  "list_my_appointments",
  "cancel_appointment",
  "reschedule_appointment",
  "request_human_handoff",
  "create_service_request",
]);

function newDemoPhone(): string {
  const suffix = Math.floor(100000 + Math.random() * 900000);
  return `+5571999${suffix}`;
}

function getDemoPhone(): string {
  try {
    const stored = window.sessionStorage.getItem("triavoz-demo-phone");
    if (stored && /^\+[1-9][0-9]{7,14}$/.test(stored)) return stored;
    const phone = newDemoPhone();
    window.sessionStorage.setItem("triavoz-demo-phone", phone);
    return phone;
  } catch {
    return newDemoPhone();
  }
}

export function DemoStage({ preview }: { preview?: string }) {
  const t = useTranslations("demo");
  const locale = useLocale();
  const [phase, setPhase] = useState<Phase>("idle");
  const [orbSpeaking, setOrbSpeaking] = useState(false);
  const [errorKind, setErrorKind] = useState<ErrorKind | null>(null);
  const [fallbackReason, setFallbackReason] = useState<string | null>(null);
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null);
  const [emergency, setEmergency] = useState(false);
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [bookingAt, setBookingAt] = useState<string | null>(null);
  const [callId, setCallId] = useState<string | null>(null);
  const [timezone, setTimezone] = useState<string | undefined>(undefined);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [endedAt, setEndedAt] = useState<number | null>(null);
  const [remaining, setRemaining] = useState(0);
  const [audioBlocked, setAudioBlocked] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);

  const roomRef = useRef<Room | null>(null);
  const audioRef = useRef<HTMLMediaElement[]>([]);
  const intentionalRef = useRef(false);
  const deadlineRef = useRef(0);
  const captionRef = useRef<HTMLDivElement | null>(null);

  const previewActive = process.env.NODE_ENV !== "production" && Boolean(preview);
  const previewPhase: PreviewPhase | undefined = previewActive ? preview : undefined;

  useEffect(() => {
    if (!previewPhase) return;
    if (previewPhase === "connecting") {
      setPhase("connecting");
      return;
    }
    if (previewPhase === "listening" || previewPhase === "speaking") {
      setPhase("live");
      setStartedAt(Date.now() - 24_000);
      deadlineRef.current = Date.now() + 276_000;
      setRemaining(276);
      setOrbSpeaking(previewPhase === "speaking");
      setCaptions([
        {
          id: "p1",
          speaker: "agent",
          text: "Olá! Sou a assistente virtual da Clínica Horizonte. Posso ajudar a marcar uma consulta?",
          at: Date.now() - 22_000,
        },
        {
          id: "p2",
          speaker: "you",
          text: "Queria marcar uma consulta com a Dra. Ana, de preferência amanhã de manhã.",
          at: Date.now() - 18_000,
        },
        {
          id: "p3",
          speaker: "agent",
          text: "Tenho amanhã às nove e meia ou às dez e quinze com a Dra. Ana. Qual prefere?",
          at: Date.now() - 15_000,
        },
      ]);
      setTools([
        { id: "t1", name: "list_services", ok: true, at: Date.now() - 20_000 },
        { id: "t2", name: "list_available_slots", ok: true, at: Date.now() - 16_000 },
      ]);
      return;
    }
    if (previewPhase === "ended") {
      setPhase("ended");
      setStartedAt(Date.now() - 64_000);
      setEndedAt(Date.now());
      setCallId("preview-call");
      const booking = new Date();
      booking.setDate(booking.getDate() + 1);
      booking.setHours(9, 30, 0, 0);
      setBookingAt(booking.toISOString());
      setCaptions([
        {
          id: "p1",
          speaker: "agent",
          text: "Pronto, sua consulta ficou para amanhã às nove e meia. Mais alguma coisa?",
          at: Date.now() - 20_000,
        },
      ]);
      setTools([{ id: "t1", name: "book_appointment", ok: true, at: Date.now() - 19_000 }]);
      return;
    }
    if (previewPhase === "fallback") {
      setPhase("fallback");
      setFallbackReason("budget");
      return;
    }
    if (previewPhase === "error") {
      setPhase("error");
      setErrorKind("network");
    }
  }, [previewPhase]);

  const teardownAudio = useCallback(() => {
    for (const element of audioRef.current) {
      element.remove();
    }
    audioRef.current = [];
  }, []);

  const disconnect = useCallback(async () => {
    intentionalRef.current = true;
    const room = roomRef.current;
    roomRef.current = null;
    teardownAudio();
    if (room) {
      try {
        await room.disconnect();
      } catch {
        /* already disconnected */
      }
    }
  }, [teardownAudio]);

  useEffect(() => {
    return () => {
      void disconnect();
    };
  }, [disconnect]);

  useEffect(() => {
    if (phase !== "live") return;
    const timer = window.setInterval(() => {
      const seconds = Math.max(0, Math.ceil((deadlineRef.current - Date.now()) / 1000));
      setRemaining(seconds);
      if (seconds <= 0) {
        window.clearInterval(timer);
        void endCall();
      }
    }, 500);
    return () => window.clearInterval(timer);
    // endCall is stable enough for a single countdown; it reads refs and state setters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => {
    const element = captionRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [captions]);

  const endCall = useCallback(async () => {
    intentionalRef.current = true;
    await disconnect();
    setEndedAt(Date.now());
    setPhase((current) => (current === "live" ? "ended" : current));
  }, [disconnect]);

  const onTranscription = useCallback((segments: TranscriptionSegment[], participant?: Participant) => {
    setCaptions((current) => {
      const map = new Map(current.map((caption) => [caption.id, caption]));
      for (const segment of segments) {
        const text = segment.text.trim();
        if (!text) continue;
        map.set(segment.id, {
          id: segment.id,
          speaker: participant?.isLocal ? "you" : "agent",
          text,
          at: Date.now(),
        });
      }
      return [...map.values()].slice(-80);
    });
  }, []);

  const onData = useCallback((payload: Uint8Array, _participant?: unknown, _kind?: unknown, topic?: string) => {
    if (topic !== "triavoz.events") return;
    try {
      const parsed = JSON.parse(new TextDecoder().decode(payload)) as {
        type?: string;
        name?: string;
        ok?: boolean;
        starts_at?: string;
      };
      if (parsed.type !== "tool" || !parsed.name) return;
      const event: ToolEvent = {
        id: `${Date.now()}-${parsed.name}`,
        name: parsed.name,
        ok: Boolean(parsed.ok),
        at: Date.now(),
        ...(parsed.starts_at ? { startsAt: parsed.starts_at } : {}),
      };
      setTools((current) => [...current, event]);
      if (parsed.name === "book_appointment" && parsed.ok && parsed.starts_at) {
        setBookingAt(parsed.starts_at);
      }
    } catch {
      /* ignore malformed provider data */
    }
  }, []);

  async function start() {
    if (phase === "requesting" || phase === "connecting" || phase === "live") return;
    setPhase("requesting");
    setErrorKind(null);
    setFallbackReason(null);
    setFallbackMessage(null);
    setEmergency(false);
    setCaptions([]);
    setTools([]);
    setBookingAt(null);
    setCallId(null);
    setEndedAt(null);
    setAudioBlocked(false);
    intentionalRef.current = false;

    let session: VoiceSession;
    try {
      session = await api<VoiceSession>("/voice/session", {
        method: "POST",
        body: JSON.stringify({ caller_number: getDemoPhone() }),
      });
    } catch (error) {
      setPhase("error");
      if (error instanceof ApiError && error.status === 429) {
        setFallbackReason("rate_limited");
        setPhase("fallback");
      } else {
        setErrorKind("session");
      }
      return;
    }

    if (session.mode !== "session" || !session.url || !session.token) {
      setFallbackReason(session.reason ?? "rate_limited");
      setFallbackMessage(session.message);
      setEmergency(session.mode === "emergency");
      setPhase("fallback");
      return;
    }

    setCallId(session.call_id);
    setTimezone(session.timezone ?? undefined);
    setPhase("connecting");
    const room = createDemoRoom({ adaptiveStream: true, dynacast: true });
    roomRef.current = room;

    room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
      if (track.kind !== Track.Kind.Audio) return;
      const element = track.attach();
      element.autoplay = true;
      element.style.display = "none";
      document.body.appendChild(element);
      audioRef.current.push(element);
    });
    room.on(RoomEvent.ActiveSpeakersChanged, (speakers: Participant[]) => {
      setOrbSpeaking(speakers.some((speaker) => !speaker.isLocal));
    });
    room.on(RoomEvent.TranscriptionReceived, onTranscription);
    room.on(RoomEvent.DataReceived, onData);
    room.on(RoomEvent.Reconnecting, () => setReconnecting(true));
    room.on(RoomEvent.Reconnected, () => setReconnecting(false));
    room.on(RoomEvent.AudioPlaybackStatusChanged, () => {
      setAudioBlocked(!room.canPlaybackAudio);
    });
    room.on(RoomEvent.Disconnected, () => {
      if (intentionalRef.current) return;
      setReconnecting(false);
      setErrorKind("network");
      setPhase("error");
    });

    try {
      await room.connect(session.url, session.token, { autoSubscribe: true, maxRetries: 2 });
      setPhase("live");
      const seconds = session.max_call_seconds ?? 300;
      setStartedAt(Date.now());
      setRemaining(seconds);
      deadlineRef.current = Date.now() + seconds * 1000;
      try {
        await room.startAudio();
      } catch {
        setAudioBlocked(true);
      }
      try {
        await room.localParticipant.setMicrophoneEnabled(true);
      } catch {
        setErrorKind("mic");
        setPhase("error");
        await disconnect();
        return;
      }
    } catch {
      setPhase("error");
      setErrorKind("network");
      await disconnect();
    }
  }

  const orbState: OrbState = useMemo(() => {
    if (phase === "connecting" || phase === "requesting") return "connecting";
    if (phase === "live") return orbSpeaking ? "speaking" : "listening";
    if (phase === "ended") return "ended";
    if (phase === "error" || phase === "fallback") return "error";
    return "idle";
  }, [phase, orbSpeaking]);

  const durationSeconds =
    startedAt && (endedAt ?? Date.now()) ? Math.max(0, Math.round(((endedAt ?? Date.now()) - startedAt) / 1000)) : 0;
  const turnCount = captions.filter((caption) => caption.speaker === "you" || caption.speaker === "agent").length;
  const fallbackKey = fallbackReason ? FALLBACK_LABEL[fallbackReason] : null;
  const statusLabel =
    phase === "connecting" || phase === "requesting"
      ? t("connecting")
      : phase === "live"
        ? orbSpeaking
          ? t("speaking")
          : t("listening")
        : phase === "ended"
          ? t("endedTitle")
          : phase === "fallback"
            ? emergency
              ? t("emergencyTitle")
              : fallbackKey
                ? t(fallbackKey as "budget")
                : t("fallbackTitle")
            : phase === "error"
              ? t("fallbackTitle")
              : t("start");

  function toolLabel(name: string): string {
    if (TOOL_KEYS.has(name)) return t(`tool_${name}` as "tool_book_appointment");
    return name.replaceAll("_", " ");
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:items-start">
      <section className="rounded-3xl border border-border bg-surface p-6 shadow-card sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary-strong">
            <Radio aria-hidden className="size-3.5" />
            {t("eyebrow")}
          </span>
          {phase === "live" && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-st-done/10 px-2.5 py-1 text-xs font-medium text-st-done">
              <span className="size-1.5 rounded-full bg-st-done" aria-hidden />
              {reconnecting ? t("networkError") : t("remaining", { seconds: remaining })}
            </span>
          )}
        </div>

        <div className="mt-6 flex flex-col items-center text-center">
          <VoiceOrb state={orbState} size="xl" label={statusLabel} />
          <p className="mt-6 text-sm font-medium" aria-live="polite">
            {phase === "live" && reconnecting ? t("networkError") : statusLabel}
          </p>
          {phase === "connecting" && <p className="mt-1 text-xs text-muted">{t("connectingHint")}</p>}
          {previewActive && (
            <span className="mt-2 rounded-full border border-border px-2 py-0.5 text-[0.62rem] uppercase tracking-wider text-muted">
              {t("preview")}
            </span>
          )}

          <div className="mt-6 flex w-full max-w-sm flex-col gap-2">
            {(phase === "idle" || phase === "ended" || phase === "error") &&
              (!previewActive || phase === "idle") && (
              <button
                type="button"
                onClick={() => void start()}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-contrast transition-colors hover:bg-primary-strong"
              >
                <Mic aria-hidden className="size-4" />
                {phase === "ended" ? t("again") : phase === "error" ? t("retry") : t("start")}
              </button>
            )}
            {phase === "live" && (
              <button
                type="button"
                onClick={() => void endCall()}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-st-urgent/35 bg-st-urgent/10 px-6 py-3 text-sm font-semibold text-st-urgent transition-colors hover:bg-st-urgent/15"
              >
                <PhoneOff aria-hidden className="size-4" />
                {t("end")}
              </button>
            )}
            {phase === "requesting" && (
              <span className="inline-flex items-center justify-center gap-2 rounded-full border border-border px-6 py-3 text-sm text-muted">
                <Loader2 aria-hidden className="size-4 animate-spin" />
                {t("connecting")}
              </span>
            )}
            {audioBlocked && phase === "live" && (
              <button
                type="button"
                onClick={async () => {
                  try {
                    await roomRef.current?.startAudio();
                    setAudioBlocked(false);
                  } catch {
                    setAudioBlocked(true);
                  }
                }}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-border px-4 py-2 text-xs font-medium"
              >
                <Volume2 aria-hidden className="size-4" />
                {t("enableAudio")}
              </button>
            )}
          </div>
          <p className="mt-3 max-w-sm text-xs text-muted">{t("disclaimer")}</p>
          <p className="mt-1 text-[0.68rem] text-muted">{t("secure")}</p>
        </div>
      </section>

      <section className="flex min-h-[28rem] flex-col gap-4">
        {phase === "fallback" && (
          <div
            role="alert"
            className={clsx(
              "rounded-2xl border p-5",
              emergency
                ? "border-st-urgent/40 bg-st-urgent/10"
                : "border-st-pending/35 bg-st-pending/10",
            )}
          >
            <div className="flex items-start gap-3">
              {emergency ? (
                <ShieldAlert aria-hidden className="mt-0.5 size-5 text-st-urgent" />
              ) : (
                <AlertTriangle aria-hidden className="mt-0.5 size-5 text-st-pending" />
              )}
              <div>
                <h2 className="text-sm font-semibold">
                  {emergency
                    ? t("emergencyTitle")
                    : fallbackKey
                      ? t(fallbackKey as "budget")
                      : t("fallbackTitle")}
                </h2>
                <p className="mt-1 text-sm text-muted">
                  {emergency
                    ? t("emergencyHint")
                    : fallbackMessage ?? t("fallbackHint")}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {emergency && (
                    <a
                      href="tel:192"
                      className="inline-flex items-center gap-1.5 rounded-full bg-st-urgent px-3.5 py-2 text-xs font-semibold text-white"
                    >
                      <ShieldAlert aria-hidden className="size-3.5" />
                      {t("emergencyCall")}
                    </a>
                  )}
                  {!emergency && !previewActive && (
                    <button
                      type="button"
                      onClick={() => void start()}
                      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-xs font-medium"
                    >
                      {t("retry")}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {phase === "error" && (
          <div role="alert" className="rounded-2xl border border-st-urgent/35 bg-st-urgent/10 p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle aria-hidden className="mt-0.5 size-5 text-st-urgent" />
              <div>
                <h2 className="text-sm font-semibold">
                  {errorKind === "mic"
                    ? t("micDenied")
                    : errorKind === "network"
                      ? t("networkError")
                      : t("sessionError")}
                </h2>
                <p className="mt-1 text-sm text-muted">
                  {errorKind === "mic" ? t("micHint") : t("networkHint")}
                </p>
                <button
                  type="button"
                  onClick={() => void start()}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-1.5 text-xs font-medium"
                >
                  {t("retry")}
                </button>
              </div>
            </div>
          </div>
        )}

        {phase === "ended" && (
          <div className="rounded-2xl border border-border bg-surface p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold">{t("endedTitle")}</h2>
                <p className="mt-1 text-xs text-muted">{t("endedHint")}</p>
              </div>
              {callId && (
                <Link
                  href={`/chamadas/${callId}`}
                  className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast"
                >
                  {t("seeDashboard")}
                  <ArrowRight aria-hidden className="size-3.5" />
                </Link>
              )}
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-xl bg-surface-2/70 p-3">
                <dt className="text-muted">{t("duration")}</dt>
                <dd className="mt-0.5 text-sm font-medium">{formatDuration(durationSeconds)}</dd>
              </div>
              <div className="rounded-xl bg-surface-2/70 p-3">
                <dt className="text-muted">{t("turns")}</dt>
                <dd className="mt-0.5 text-sm font-medium">{turnCount}</dd>
              </div>
            </dl>
            {bookingAt && (
              <div className="mt-3 rounded-xl border border-st-done/30 bg-st-done/10 p-3 text-xs">
                <p className="flex items-center gap-1.5 font-medium text-st-done">
                  <Check aria-hidden className="size-3.5" />
                  {t("bookingTitle")}
                </p>
                <p className="mt-1 text-muted">
                  {formatDateTime(bookingAt, locale, timezone)} · {t("bookingHint")}
                </p>
              </div>
            )}
          </div>
        )}

        <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-border bg-surface">
          <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <Radio aria-hidden className="size-4 text-primary-strong" />
              {t("captionsTitle")}
            </h2>
            {phase === "live" && (
              <span className="inline-flex items-center gap-1.5 text-[0.68rem] font-medium text-st-done">
                <span className="size-1.5 animate-pulse rounded-full bg-st-done" aria-hidden />
                {t("eyebrow")}
              </span>
            )}
          </div>
          <div
            ref={captionRef}
            className="transcript-scroll max-h-72 min-h-40 flex-1 space-y-3 overflow-y-auto p-4"
            role="log"
            aria-live="polite"
            aria-label={t("captionsTitle")}
          >
            {captions.length === 0 && (
              <p className="py-8 text-center text-xs text-muted">{t("captionsEmpty")}</p>
            )}
            {captions.map((caption) => (
              <div
                key={caption.id}
                className={clsx(
                  "max-w-[88%] rounded-2xl px-3.5 py-2 text-sm",
                  caption.speaker === "you"
                    ? "ml-auto rounded-br-md bg-primary text-primary-contrast"
                    : "rounded-bl-md bg-surface-2 text-text",
                )}
              >
                <span className="mb-0.5 block text-[0.62rem] font-semibold uppercase tracking-wider opacity-70">
                  {caption.speaker === "you" ? t("you") : t("agent")}
                </span>
                {caption.text}
              </div>
            ))}
          </div>

          <div className="border-t border-border p-3">
            <h3 className="mb-2 flex items-center gap-1.5 px-1 text-[0.68rem] font-semibold uppercase tracking-wider text-muted">
              <Wrench aria-hidden className="size-3.5" />
              {t("toolsTitle")}
            </h3>
            <ul className="space-y-1.5" aria-live="polite">
              {tools.length === 0 && <li className="px-1 text-xs text-muted">—</li>}
              {tools.map((tool) => (
                <li
                  key={tool.id}
                  className={clsx(
                    "flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs",
                    tool.ok
                      ? "border-st-done/25 bg-st-done/5 text-st-done"
                      : "border-st-urgent/25 bg-st-urgent/5 text-st-urgent",
                  )}
                >
                  {tool.ok ? (
                    <Check aria-hidden className="size-3.5" />
                  ) : (
                    <X aria-hidden className="size-3.5" />
                  )}
                  <span className="flex-1">{toolLabel(tool.name)}</span>
                  <span className="text-[0.62rem] uppercase tracking-wider opacity-70">
                    {tool.ok ? t("toolDone") : t("toolError")}
                  </span>
                </li>
              ))}
            </ul>
            {bookingAt && (
              <div className="mt-3 rounded-xl border border-st-done/30 bg-st-done/10 p-3 text-xs">
                <p className="flex items-center gap-1.5 font-medium text-st-done">
                  <Clock3 aria-hidden className="size-3.5" />
                  {t("bookingTitle")}
                </p>
                <p className="mt-1 text-muted">{formatDateTime(bookingAt, locale, timezone)}</p>
                <p className="mt-0.5 text-[0.68rem] text-muted">{t("bookingHint")}</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
