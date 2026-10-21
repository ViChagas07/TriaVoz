"use client";

import { Check, History, Loader2, Rocket, Save, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { clsx } from "clsx";
import { StatusPill } from "@/components/StatusPill";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AgentConfig, AgentConfigState, ClinicSettings, ConfigVersion } from "@/lib/types";

export function AgentEditor({
  state,
  versions,
  limits,
}: {
  state: AgentConfigState;
  versions: ConfigVersion[];
  limits: ClinicSettings;
}) {
  const t = useTranslations("agent");
  const errors = useTranslations("errors");
  const router = useRouter();
  const locale = useLocale();
  const base = state.latest_draft?.config ?? state.published?.config;
  const [form, setForm] = useState<AgentConfig>(
    base ?? {
      schema_version: 1,
      clinic_name: limits.name,
      greeting: "Olá! Sou a assistente virtual da {clinic_name}. Como posso ajudar?",
      tone: "acolhedor, claro e objetivo",
      emergency_message: "Se for uma emergência, ligue agora para o SAMU, no 192.",
    },
  );
  const [draft, setDraft] = useState(state.latest_draft);
  const [published, setPublished] = useState(state.published);
  const [busy, setBusy] = useState<null | "save" | "publish" | `rollback:${number}`>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const dirty = useMemo(() => {
    const source = draft?.config ?? published?.config;
    if (!source) return true;
    return JSON.stringify(source) !== JSON.stringify(form);
  }, [draft, published, form]);

  function update<K extends keyof AgentConfig>(key: K, value: AgentConfig[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function saveDraft() {
    setBusy("save");
    setError(null);
    setMessage(null);
    try {
      const saved = await api<ConfigVersion>("/agent-config/draft", {
        method: "PUT",
        body: JSON.stringify(form),
      });
      setDraft(saved);
      setMessage(t("saved"));
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 403 ? errors("forbidden") : t("error"));
    } finally {
      setBusy(null);
    }
  }

  async function publish() {
    const version = draft?.version ?? published?.version;
    if (!version) return;
    setBusy("publish");
    setError(null);
    setMessage(null);
    try {
      const result = await api<ConfigVersion>(`/agent-config/${version}/publish`, {
        method: "POST",
      });
      setPublished(result);
      setDraft(null);
      setMessage(t("publishedOk"));
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 403 ? errors("forbidden") : t("error"));
    } finally {
      setBusy(null);
    }
  }

  async function rollback(version: number) {
    setBusy(`rollback:${version}`);
    setError(null);
    setMessage(null);
    try {
      const result = await api<ConfigVersion>(`/agent-config/${version}/rollback`, {
        method: "POST",
      });
      setPublished(result);
      setMessage(t("rollbackOk"));
      router.refresh();
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 403 ? errors("forbidden") : t("error"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
      <section className="rounded-2xl border border-border bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold">{t("published")}</h2>
            <p className="text-[0.68rem] text-muted">
              {published ? t("version", { version: published.version }) : t("noDraft")}
            </p>
          </div>
          {published && <StatusPill status="published" />}
        </div>

        <div className="space-y-4 p-5">
          <label className="grid gap-1 text-sm">
            <span className="font-medium">{t("clinicName")}</span>
            <input
              value={form.clinic_name}
              maxLength={120}
              onChange={(event) => update("clinic_name", event.target.value)}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="flex items-center justify-between gap-2 font-medium">
              {t("greeting")}
              <span className="text-[0.62rem] font-normal text-muted">{t("greetingHint")}</span>
            </span>
            <textarea
              value={form.greeting}
              maxLength={500}
              rows={3}
              onChange={(event) => update("greeting", event.target.value)}
              className="resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="flex items-center justify-between gap-2 font-medium">
              {t("tone")}
              <span className="text-[0.62rem] font-normal text-muted">{t("toneHint")}</span>
            </span>
            <input
              value={form.tone}
              maxLength={200}
              onChange={(event) => update("tone", event.target.value)}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="flex items-center justify-between gap-2 font-medium">
              {t("emergencyMessage")}
              <span className="text-[0.62rem] font-normal text-muted">{t("emergencyHint")}</span>
            </span>
            <textarea
              value={form.emergency_message}
              maxLength={300}
              rows={2}
              onChange={(event) => update("emergency_message", event.target.value)}
              className="resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm"
            />
          </label>

          {message && (
            <p role="status" className="rounded-lg border border-st-done/30 bg-st-done/10 px-3 py-2 text-xs text-st-done">
              {message}
            </p>
          )}
          {error && (
            <p role="alert" className="rounded-lg border border-st-urgent/30 bg-st-urgent/10 px-3 py-2 text-xs text-st-urgent">
              {error}
            </p>
          )}
        </div>

        <div className="sticky bottom-0 border-t border-border bg-surface/95 px-5 py-3 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[0.68rem] text-muted">
              {dirty ? t("draftNotice") : t("stickyHint")}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={saveDraft}
                disabled={busy !== null}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-xs font-medium disabled:opacity-60"
              >
                {busy === "save" ? <Loader2 aria-hidden className="size-3.5 animate-spin" /> : <Save aria-hidden className="size-3.5" />}
                {busy === "save" ? t("saving") : t("saveDraft")}
              </button>
              <button
                type="button"
                onClick={publish}
                disabled={busy !== null || !draft}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast disabled:opacity-60"
              >
                {busy === "publish" ? <Loader2 aria-hidden className="size-3.5 animate-spin" /> : <Rocket aria-hidden className="size-3.5" />}
                {busy === "publish" ? t("publishing") : t("publish")}
              </button>
            </div>
          </div>
        </div>
      </section>

      <div className="space-y-4">
        <section className="rounded-2xl border border-border bg-surface p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck aria-hidden className="size-4 text-primary-strong" />
              {t("limitsTitle")}
            </h2>
            <Link href="/configuracoes" className="text-[0.68rem] font-medium text-primary-strong">
              {t("editLimits")}
            </Link>
          </div>
          <p className="mt-1 text-xs text-muted">{t("limitsHint")}</p>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
            {[
              [t("maxCall"), `${limits.max_call_seconds}s`],
              [t("maxTurns"), "20"],
              [t("silence"), "15s"],
              [t("concurrency"), String(limits.max_concurrent_calls)],
              [t("dailyMinutes"), `${limits.daily_minute_budget} min`],
              [t("dailyCost"), `R$ ${(limits.daily_cost_budget_cents / 100).toFixed(2)}`],
              [t("killSwitch"), limits.kill_switch ? t("on") : t("off")],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-surface-2/70 p-3">
                <dt className="text-muted">{label}</dt>
                <dd className="mt-0.5 font-medium">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-[0.62rem] text-muted">{t("readonly")}</p>
        </section>

        <section className="rounded-2xl border border-border bg-surface p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <History aria-hidden className="size-4 text-primary-strong" />
            {t("versions")}
          </h2>
          <ol className="mt-3 divide-y divide-border">
            {versions.map((version) => (
              <li key={version.id} className="flex items-center gap-2 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium">{t("version", { version: version.version })}</p>
                  <p className="text-[0.62rem] text-muted">
                    {formatDateTime(version.published_at ?? version.created_at, locale)}
                  </p>
                </div>
                <StatusPill status={version.status} />
                {version.status !== "published" && (
                  <button
                    type="button"
                    onClick={() => rollback(version.version)}
                    disabled={busy !== null}
                    className="rounded-full border border-border px-2 py-1 text-[0.62rem] font-medium disabled:opacity-60"
                  >
                    {busy === `rollback:${version.version}` ? t("rollingBack") : t("rollback")}
                  </button>
                )}
                {draft?.version === version.version && (
                  <button
                    type="button"
                    onClick={publish}
                    disabled={busy !== null}
                    className={clsx(
                      "inline-flex items-center gap-1 rounded-full bg-primary px-2 py-1 text-[0.62rem] font-semibold text-primary-contrast",
                    )}
                  >
                    <Check aria-hidden className="size-3" />
                    {t("publish")}
                  </button>
                )}
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}
