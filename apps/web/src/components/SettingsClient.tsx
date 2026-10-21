"use client";

import { Check, Loader2, Plus, Power, Save, ShieldAlert, Trash2, UserPlus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";
import { clsx } from "clsx";
import { StatusPill } from "@/components/StatusPill";
import { api, apiVoid, ApiError } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import type {
  BlockedNumber,
  BusinessHours,
  ClinicSettings,
  Professional,
  Service,
  TeamUser,
} from "@/lib/types";

type Tab = "clinic" | "services" | "professionals" | "blocked" | "team";

const INPUT =
  "w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-primary";

const DAY_KEYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;

export function SettingsClient({
  tab,
  settings,
  services,
  professionals,
  blocked,
  team,
  canManage,
}: {
  tab: Tab;
  settings: ClinicSettings;
  services: Service[];
  professionals: Professional[];
  blocked: BlockedNumber[];
  team: TeamUser[];
  canManage: boolean;
}) {
  const t = useTranslations("settings");
  const common = useTranslations("common");
  const errors = useTranslations("errors");
  const router = useRouter();
  const locale = useLocale();
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function fail(caught: unknown) {
    setError(
      caught instanceof ApiError && caught.status === 403 ? errors("forbidden") : t("error"),
    );
  }

  async function mutate(label: string, action: () => Promise<void>) {
    if (!canManage) return;
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      await action();
      router.refresh();
    } catch (caught) {
      fail(caught);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {!canManage && (
        <p className="rounded-xl border border-st-pending/30 bg-st-pending/10 px-4 py-3 text-xs text-st-pending">
          {t("adminOnly")}
        </p>
      )}
      {message && (
        <p role="status" className="rounded-xl border border-st-done/30 bg-st-done/10 px-4 py-3 text-xs text-st-done">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="rounded-xl border border-st-urgent/30 bg-st-urgent/10 px-4 py-3 text-xs text-st-urgent">
          {error}
        </p>
      )}

      {tab === "clinic" && (
        <ClinicForm
          initial={settings}
          busy={busy}
          canManage={canManage}
          onSave={async (body) => {
            await mutate("clinic", async () => {
              await api<ClinicSettings>("/settings/clinic", {
                method: "PUT",
                body: JSON.stringify(body),
              });
              setMessage(t("saved"));
            });
          }}
        />
      )}

      {tab === "services" && (
        <ServicesPanel
          initial={services}
          busy={busy}
          canManage={canManage}
          locale={locale}
          onCreate={(body) =>
            mutate("service-create", async () => {
              await api<Service>("/services", { method: "POST", body: JSON.stringify(body) });
              setMessage(t("created"));
            })
          }
          onUpdate={(id, body) =>
            mutate(`service-${id}`, async () => {
              await api<Service>(`/services/${id}`, {
                method: "PATCH",
                body: JSON.stringify(body),
              });
              setMessage(common("saved"));
            })
          }
          onDelete={(id) =>
            mutate(`service-delete-${id}`, async () => {
              await apiVoid(`/services/${id}`, { method: "DELETE" });
              setMessage(t("deactivated"));
            })
          }
        />
      )}

      {tab === "professionals" && (
        <ProfessionalsPanel
          initial={professionals}
          services={services}
          busy={busy}
          canManage={canManage}
          onCreate={(body) =>
            mutate("professional-create", async () => {
              await api<Professional>("/professionals", {
                method: "POST",
                body: JSON.stringify(body),
              });
              setMessage(t("created"));
            })
          }
          onUpdate={(id, body) =>
            mutate(`professional-${id}`, async () => {
              await api<Professional>(`/professionals/${id}`, {
                method: "PATCH",
                body: JSON.stringify(body),
              });
              setMessage(common("saved"));
            })
          }
          onDelete={(id) =>
            mutate(`professional-delete-${id}`, async () => {
              await apiVoid(`/professionals/${id}`, { method: "DELETE" });
              setMessage(t("deactivated"));
            })
          }
        />
      )}

      {tab === "blocked" && (
        <BlockedPanel
          initial={blocked}
          busy={busy}
          canManage={canManage}
          locale={locale}
          onCreate={(body) =>
            mutate("blocked-create", async () => {
              await api<BlockedNumber>("/blocked-numbers", {
                method: "POST",
                body: JSON.stringify(body),
              });
              setMessage(t("created"));
            })
          }
          onDelete={(id) =>
            mutate(`blocked-${id}`, async () => {
              await apiVoid(`/blocked-numbers/${id}/unblock`, { method: "POST" });
              setMessage(t("deactivated"));
            })
          }
        />
      )}

      {tab === "team" && (
        <TeamPanel
          initial={team}
          busy={busy}
          canManage={canManage}
          onCreate={(body) =>
            mutate("user-create", async () => {
              await api<TeamUser>("/team", { method: "POST", body: JSON.stringify(body) });
              setMessage(t("created"));
            })
          }
          onDelete={(id) =>
            mutate(`user-${id}`, async () => {
              await apiVoid(`/team/${id}`, { method: "DELETE" });
              setMessage(t("deactivated"));
            })
          }
        />
      )}
    </div>
  );
}

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-border bg-surface p-5">
      <h2 className="text-sm font-semibold">{title}</h2>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function ClinicForm({
  initial,
  busy,
  canManage,
  onSave,
}: {
  initial: ClinicSettings;
  busy: string | null;
  canManage: boolean;
  onSave: (body: {
    name: string;
    timezone: string;
    business_hours: BusinessHours | null;
    max_call_seconds: number;
    max_concurrent_calls: number;
    daily_minute_budget: number;
    daily_cost_budget_cents: number;
    kill_switch: boolean;
    hidden_caller_policy: "allow" | "reject";
  }) => Promise<void>;
}) {
  const t = useTranslations("settings");
  const [form, setForm] = useState(initial);
  const [usesHours, setUsesHours] = useState(Boolean(initial.business_hours));
  const [hours, setHours] = useState<BusinessHours>(
    initial.business_hours ?? { days: [1, 2, 3, 4, 5], start: "08:00", end: "18:00" },
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSave({
      name: form.name,
      timezone: form.timezone,
      business_hours: usesHours ? hours : null,
      max_call_seconds: form.max_call_seconds,
      max_concurrent_calls: form.max_concurrent_calls,
      daily_minute_budget: form.daily_minute_budget,
      daily_cost_budget_cents: form.daily_cost_budget_cents,
      kill_switch: form.kill_switch,
      hidden_caller_policy: form.hidden_caller_policy,
    });
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Section title={t("clinicTitle")}>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1 text-xs">
            <span className="font-medium text-muted">{t("name")}</span>
            <input
              required
              disabled={!canManage}
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              className={INPUT}
            />
          </label>
          <label className="grid gap-1 text-xs">
            <span className="font-medium text-muted">{t("timezone")}</span>
            <input
              required
              disabled={!canManage}
              value={form.timezone}
              onChange={(event) => setForm({ ...form, timezone: event.target.value })}
              className={INPUT}
              placeholder="America/Bahia"
            />
          </label>
        </div>

        <div className="mt-4 rounded-xl border border-border bg-surface-2/40 p-3">
          <label className="flex items-center gap-2 text-xs font-medium">
            <input
              type="checkbox"
              checked={usesHours}
              disabled={!canManage}
              onChange={(event) => setUsesHours(event.target.checked)}
            />
            {t("hours")}
          </label>
          {usesHours && (
            <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
              <fieldset className="flex flex-wrap gap-1.5">
                <legend className="mb-1 text-[0.68rem] text-muted">{t("days")}</legend>
                {DAY_KEYS.map((key, index) => {
                  const day = index + 1;
                  const checked = hours.days.includes(day);
                  return (
                    <label
                      key={key}
                      className={clsx(
                        "cursor-pointer rounded-full border px-2 py-1 text-[0.68rem]",
                        checked
                          ? "border-primary/30 bg-primary/10 text-primary-strong"
                          : "border-border text-muted",
                      )}
                    >
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={checked}
                        disabled={!canManage}
                        onChange={(event) =>
                          setHours({
                            ...hours,
                            days: event.target.checked
                              ? [...hours.days, day].sort()
                              : hours.days.filter((value) => value !== day),
                          })
                        }
                      />
                      {t(key)}
                    </label>
                  );
                })}
              </fieldset>
              <label className="grid gap-1 text-xs">
                <span className="text-muted">{t("start")}</span>
                <input
                  type="time"
                  value={hours.start}
                  disabled={!canManage}
                  onChange={(event) => setHours({ ...hours, start: event.target.value })}
                  className={INPUT}
                />
              </label>
              <label className="grid gap-1 text-xs">
                <span className="text-muted">{t("end")}</span>
                <input
                  type="time"
                  value={hours.end}
                  disabled={!canManage}
                  onChange={(event) => setHours({ ...hours, end: event.target.value })}
                  className={INPUT}
                />
              </label>
            </div>
          )}
        </div>
      </Section>

      <Section title={t("limitsTitle")} hint={t("advancedHint")}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(
            [
              ["max_call_seconds", t("maxCall")],
              ["max_concurrent_calls", t("maxConcurrent")],
              ["daily_minute_budget", t("dailyMinutes")],
              ["daily_cost_budget_cents", t("dailyCost")],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="grid gap-1 text-xs">
              <span className="font-medium text-muted">{label}</span>
              <input
                required
                type="number"
                min={0}
                disabled={!canManage}
                value={form[key]}
                onChange={(event) => setForm({ ...form, [key]: Number(event.target.value) })}
                className={INPUT}
              />
            </label>
          ))}
          <label className="grid gap-1 text-xs">
            <span className="font-medium text-muted">{t("hiddenPolicy")}</span>
            <select
              value={form.hidden_caller_policy}
              disabled={!canManage}
              onChange={(event) =>
                setForm({ ...form, hidden_caller_policy: event.target.value as "allow" | "reject" })
              }
              className={INPUT}
            >
              <option value="allow">{t("allowHidden")}</option>
              <option value="reject">{t("rejectHidden")}</option>
            </select>
          </label>
          <label className="flex items-center gap-2 self-end rounded-lg border border-border px-3 py-2 text-xs">
            <input
              type="checkbox"
              checked={form.kill_switch}
              disabled={!canManage}
              onChange={(event) => setForm({ ...form, kill_switch: event.target.checked })}
            />
            {t("killSwitch")}
          </label>
        </div>
      </Section>

      <button
        type="submit"
        disabled={busy !== null || !canManage}
        className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-contrast disabled:opacity-60"
      >
        {busy === "clinic" ? <Loader2 aria-hidden className="size-4 animate-spin" /> : <Save aria-hidden className="size-4" />}
        {busy === "clinic" ? t("saving") : t("save")}
      </button>
    </form>
  );
}

type ServiceBody = { name: string; duration_min: number; price_cents: number };

function ServicesPanel({
  initial,
  busy,
  canManage,
  locale,
  onCreate,
  onUpdate,
  onDelete,
}: {
  initial: Service[];
  busy: string | null;
  canManage: boolean;
  locale: string;
  onCreate: (body: ServiceBody) => Promise<void>;
  onUpdate: (id: string, body: Partial<ServiceBody> & { is_active?: boolean }) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const t = useTranslations("settings");
  const common = useTranslations("common");
  const [items, setItems] = useState(initial);
  const [name, setName] = useState("");
  const [duration, setDuration] = useState(30);
  const [price, setPrice] = useState(0);
  useEffect(() => setItems(initial), [initial]);
  const [editing, setEditing] = useState<string | null>(null);
  const [edit, setEdit] = useState<ServiceBody>({ name: "", duration_min: 30, price_cents: 0 });

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCreate({ name: name.trim(), duration_min: duration, price_cents: price });
    setName("");
    setDuration(30);
    setPrice(0);
  }

  return (
    <Section title={t("servicesTitle")}>
      <form onSubmit={add} className="grid gap-3 sm:grid-cols-[1.4fr_0.6fr_0.6fr_auto]">
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("serviceName")}</span>
          <input required disabled={!canManage} value={name} onChange={(event) => setName(event.target.value)} className={INPUT} />
        </label>
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("duration")}</span>
          <input required type="number" min={1} max={480} disabled={!canManage} value={duration} onChange={(event) => setDuration(Number(event.target.value))} className={INPUT} />
        </label>
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("price")}</span>
          <input required type="number" min={0} disabled={!canManage} value={price} onChange={(event) => setPrice(Number(event.target.value))} className={INPUT} />
        </label>
        <button type="submit" disabled={!canManage || busy !== null} className="inline-flex items-center justify-center gap-1.5 self-end rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-contrast disabled:opacity-60">
          <Plus aria-hidden className="size-3.5" />
          {t("addService")}
        </button>
      </form>

      {items.length === 0 ? (
        <p className="mt-4 text-xs text-muted">{t("noServices")}</p>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {items.map((service) => (
            <li key={service.id} className="py-3">
              {editing === service.id ? (
                <div className="grid gap-2 sm:grid-cols-[1.4fr_0.6fr_0.6fr_auto_auto]">
                  <input value={edit.name} onChange={(event) => setEdit({ ...edit, name: event.target.value })} className={INPUT} aria-label={t("serviceName")} />
                  <input type="number" min={1} value={edit.duration_min} onChange={(event) => setEdit({ ...edit, duration_min: Number(event.target.value) })} className={INPUT} aria-label={t("duration")} />
                  <input type="number" min={0} value={edit.price_cents} onChange={(event) => setEdit({ ...edit, price_cents: Number(event.target.value) })} className={INPUT} aria-label={t("price")} />
                  <button
                    type="button"
                    onClick={async () => {
                      await onUpdate(service.id, edit);
                      setItems((current) => current.map((item) => (item.id === service.id ? { ...item, ...edit } : item)));
                      setEditing(null);
                    }}
                    className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-contrast"
                  >
                    {common("save")}
                  </button>
                  <button type="button" onClick={() => setEditing(null)} className="rounded-lg border border-border px-3 py-2 text-xs">
                    {common("cancel")}
                  </button>
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{service.name}</p>
                    <p className="text-[0.68rem] text-muted">
                      {service.duration_min} min · {formatMoney(service.price_cents, locale)}
                    </p>
                  </div>
                  <StatusPill status={service.is_active ? "active" : "inactive"} />
                  <button type="button" disabled={!canManage} onClick={() => { setEditing(service.id); setEdit({ name: service.name, duration_min: service.duration_min, price_cents: service.price_cents }); }} className="rounded-full border border-border px-2.5 py-1 text-[0.68rem]">
                    {common("edit")}
                  </button>
                  <button
                    type="button"
                    disabled={!canManage || !service.is_active}
                    onClick={async () => {
                      await onDelete(service.id);
                      setItems((current) => current.map((item) => (item.id === service.id ? { ...item, is_active: false } : item)));
                    }}
                    className="text-muted hover:text-st-urgent disabled:opacity-40"
                    aria-label={common("delete")}
                  >
                    <Trash2 aria-hidden className="size-3.5" />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

type ProfessionalBody = { name: string; specialty: string | null; service_ids: string[] };

function ProfessionalsPanel({
  initial,
  services,
  busy,
  canManage,
  onCreate,
  onUpdate,
  onDelete,
}: {
  initial: Professional[];
  services: Service[];
  busy: string | null;
  canManage: boolean;
  onCreate: (body: ProfessionalBody) => Promise<void>;
  onUpdate: (id: string, body: Partial<ProfessionalBody> & { is_active?: boolean }) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const t = useTranslations("settings");
  const common = useTranslations("common");
  const [items, setItems] = useState(initial);
  const [name, setName] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [serviceIds, setServiceIds] = useState<string[]>([]);
  useEffect(() => setItems(initial), [initial]);

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCreate({ name: name.trim(), specialty: specialty.trim() || null, service_ids: serviceIds });
    setName("");
    setSpecialty("");
    setServiceIds([]);
  }

  return (
    <Section title={t("professionalsTitle")}>
      <form onSubmit={add} className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("professionalName")}</span>
          <input required disabled={!canManage} value={name} onChange={(event) => setName(event.target.value)} className={INPUT} />
        </label>
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("specialty")}</span>
          <input disabled={!canManage} value={specialty} onChange={(event) => setSpecialty(event.target.value)} className={INPUT} />
        </label>
        <fieldset className="sm:col-span-2">
          <legend className="mb-1 text-xs text-muted">{t("services")}</legend>
          <div className="flex flex-wrap gap-1.5">
            {services.filter((service) => service.is_active).map((service) => {
              const checked = serviceIds.includes(service.id);
              return (
                <label key={service.id} className={clsx("cursor-pointer rounded-full border px-2 py-1 text-[0.68rem]", checked ? "border-primary/30 bg-primary/10 text-primary-strong" : "border-border text-muted")}>
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    onChange={(event) =>
                      setServiceIds(
                        event.target.checked
                          ? [...serviceIds, service.id]
                          : serviceIds.filter((id) => id !== service.id),
                      )
                    }
                  />
                  {service.name}
                </label>
              );
            })}
          </div>
        </fieldset>
        <button type="submit" disabled={!canManage || busy !== null} className="inline-flex items-center justify-center gap-1.5 justify-self-start rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast disabled:opacity-60">
          <UserPlus aria-hidden className="size-3.5" />
          {t("addProfessional")}
        </button>
      </form>

      {items.length === 0 ? (
        <p className="mt-4 text-xs text-muted">{t("noProfessionals")}</p>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {items.map((professional) => (
            <li key={professional.id} className="flex flex-wrap items-center gap-2 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{professional.name}</p>
                <p className="text-[0.68rem] text-muted">{professional.specialty ?? "—"}</p>
              </div>
              <StatusPill status={professional.is_active ? "active" : "inactive"} />
              <button
                type="button"
                disabled={!canManage}
                onClick={async () => {
                  await onUpdate(professional.id, { is_active: !professional.is_active });
                  setItems((current) =>
                    current.map((item) =>
                      item.id === professional.id
                        ? { ...item, is_active: !professional.is_active }
                        : item,
                    ),
                  );
                }}
                aria-label={t("active")}
                className="text-muted hover:text-primary-strong disabled:opacity-40"
              >
                <Power aria-hidden className="size-3.5" />
              </button>
              <button
                type="button"
                disabled={!canManage || !professional.is_active}
                onClick={async () => {
                  await onDelete(professional.id);
                  setItems((current) => current.map((item) => (item.id === professional.id ? { ...item, is_active: false } : item)));
                }}
                className="text-muted hover:text-st-urgent disabled:opacity-40"
                aria-label={common("delete")}
              >
                <Trash2 aria-hidden className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function BlockedPanel({
  initial,
  busy,
  canManage,
  locale,
  onCreate,
  onDelete,
}: {
  initial: BlockedNumber[];
  busy: string | null;
  canManage: boolean;
  locale: string;
  onCreate: (body: { e164: string; reason: string | null; expires_in_days: number | null }) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const t = useTranslations("settings");
  const [items, setItems] = useState(initial);
  const [e164, setE164] = useState("");
  const [reason, setReason] = useState("");
  const [days, setDays] = useState("");
  useEffect(() => setItems(initial), [initial]);

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCreate({
      e164: e164.trim(),
      reason: reason.trim() || null,
      expires_in_days: days ? Number(days) : null,
    });
    setE164("");
    setReason("");
    setDays("");
  }

  return (
    <Section title={t("blockedTitle")}>
      <form onSubmit={add} className="grid gap-3 sm:grid-cols-[1fr_1fr_0.5fr_auto]">
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("e164")}</span>
          <input required pattern="^\+[1-9][0-9]{7,14}$" placeholder="+5511999999999" disabled={!canManage} value={e164} onChange={(event) => setE164(event.target.value)} className={INPUT} />
        </label>
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("reason")}</span>
          <input disabled={!canManage} value={reason} onChange={(event) => setReason(event.target.value)} className={INPUT} />
        </label>
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("expiresDays")}</span>
          <input type="number" min={1} max={3650} disabled={!canManage} value={days} onChange={(event) => setDays(event.target.value)} className={INPUT} />
        </label>
        <button type="submit" disabled={!canManage || busy !== null} className="inline-flex items-center justify-center gap-1.5 self-end rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-contrast disabled:opacity-60">
          <ShieldAlert aria-hidden className="size-3.5" />
          {t("addBlocked")}
        </button>
      </form>

      {items.length === 0 ? (
        <p className="mt-4 text-xs text-muted">{t("noBlocked")}</p>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center gap-2 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium tabular-nums">{item.e164}</p>
                <p className="text-[0.68rem] text-muted">
                  {item.reason ?? item.source} ·{" "}
                  {item.expires_at ? t("expiresAt", { date: formatDate(item.expires_at, locale) }) : t("permanent")}
                </p>
              </div>
              <button
                type="button"
                disabled={!canManage}
                onClick={async () => {
                  await onDelete(item.id);
                  setItems((current) => current.filter((row) => row.id !== item.id));
                }}
                className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-[0.68rem]"
              >
                <Check aria-hidden className="size-3" />
                {t("unblock")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function TeamPanel({
  initial,
  busy,
  canManage,
  onCreate,
  onDelete,
}: {
  initial: TeamUser[];
  busy: string | null;
  canManage: boolean;
  onCreate: (body: { email: string; full_name: string; role: "admin" | "attendant"; password: string }) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const t = useTranslations("settings");
  const [items, setItems] = useState(initial);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<"admin" | "attendant">("attendant");
  const [password, setPassword] = useState("");
  useEffect(() => setItems(initial), [initial]);

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCreate({ email: email.trim(), full_name: fullName.trim(), role, password });
    setEmail("");
    setFullName("");
    setRole("attendant");
    setPassword("");
  }

  return (
    <Section title={t("teamTitle")}>
      <form onSubmit={add} className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("fullName")}</span>
          <input required disabled={!canManage} value={fullName} onChange={(event) => setFullName(event.target.value)} className={INPUT} />
        </label>
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("email")}</span>
          <input required type="email" disabled={!canManage} value={email} onChange={(event) => setEmail(event.target.value)} className={INPUT} />
        </label>
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("role")}</span>
          <select value={role} disabled={!canManage} onChange={(event) => setRole(event.target.value as "admin" | "attendant")} className={INPUT}>
            <option value="attendant">{t("attendant")}</option>
            <option value="admin">{t("admin")}</option>
          </select>
        </label>
        <label className="grid gap-1 text-xs">
          <span className="text-muted">{t("password")}</span>
          <input required type="password" minLength={10} disabled={!canManage} value={password} onChange={(event) => setPassword(event.target.value)} className={INPUT} />
        </label>
        <button type="submit" disabled={!canManage || busy !== null} className="inline-flex items-center justify-center gap-1.5 justify-self-start rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast disabled:opacity-60">
          <UserPlus aria-hidden className="size-3.5" />
          {t("addUser")}
        </button>
      </form>

      {items.length === 0 ? (
        <p className="mt-4 text-xs text-muted">{t("noTeam")}</p>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {items.map((member) => (
            <li key={member.id} className="flex flex-wrap items-center gap-2 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{member.full_name}</p>
                <p className="text-[0.68rem] text-muted">
                  {member.email} · {member.role === "admin" ? t("admin") : t("attendant")}
                </p>
              </div>
              <StatusPill status={member.is_active ? "active" : "inactive"} />
              <button
                type="button"
                disabled={!canManage || !member.is_active}
                onClick={async () => {
                  if (!window.confirm(t("confirmDeactivate"))) return;
                  await onDelete(member.id);
                  setItems((current) => current.map((item) => (item.id === member.id ? { ...item, is_active: false } : item)));
                }}
                className="text-muted hover:text-st-urgent disabled:opacity-40"
                aria-label={t("deactivate")}
              >
                <Trash2 aria-hidden className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

