"use client";

import { ArrowRight, Building2, Eye, EyeOff, Lock, Mail, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { clsx } from "clsx";
import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "@/lib/demo-accounts";

export function LoginForm({ nextPath }: { nextPath: string }) {
  const t = useTranslations("auth");
  const errors = useTranslations("errors");
  const router = useRouter();
  const [clinic, setClinic] = useState("clinica-horizonte");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clinic_code: clinic.trim(), email: email.trim(), password }),
      });
      if (!response.ok) {
        if (response.status === 429) setError(t("errorLocked"));
        else if (response.status >= 500) setError(errors("network"));
        else setError(t("errorGeneric"));
        return;
      }
      router.replace(nextPath);
      router.refresh();
    } catch {
      setError(t("errorNetwork"));
    } finally {
      setSubmitting(false);
    }
  }

  function useDemo(index: number) {
    const account = DEMO_ACCOUNTS[index];
    if (!account) return;
    setClinic(account.clinic);
    setEmail(account.email);
    setPassword(DEMO_PASSWORD);
    setError(null);
  }

  return (
    <div className="mx-auto grid w-full max-w-5xl gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
      <section className="hidden lg:block">
        <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary-strong">
          <ShieldCheck aria-hidden className="size-3.5" />
          {t("demoHint")}
        </p>
        <h2 className="text-balance text-4xl font-semibold tracking-tight">
          {t("title")}
        </h2>
        <p className="mt-4 max-w-md text-sm leading-relaxed text-muted">{t("subtitle")}</p>
        <div className="mt-8 grid gap-2">
          {DEMO_ACCOUNTS.map((account, index) => (
            <button
              key={account.key}
              type="button"
              onClick={() => useDemo(index)}
              className="group flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3 text-left transition-colors hover:border-primary/40 hover:bg-primary/5"
            >
              <span>
                <span className="block text-sm font-medium">{account.email}</span>
                <span className="block text-xs text-muted">
                  {account.clinic} · {t(account.labelKey)}
                </span>
              </span>
              <ArrowRight
                aria-hidden
                className="size-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-primary-strong"
              />
            </button>
          ))}
        </div>
      </section>

      <form
        onSubmit={onSubmit}
        className="rounded-2xl border border-border bg-surface p-6 shadow-card sm:p-8"
        aria-describedby={error ? "login-error" : undefined}
      >
        <div className="mb-6">
          <h1 className="text-xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("subtitle")}</p>
        </div>

        <div className="space-y-4">
          <label className="block text-sm">
            <span className="mb-1.5 flex items-center gap-1.5 font-medium">
              <Building2 aria-hidden className="size-3.5 text-muted" />
              {t("clinic")}
            </span>
            <input
              required
              name="clinic"
              value={clinic}
              onChange={(event) => setClinic(event.target.value)}
              autoComplete="organization"
              placeholder={t("clinicPlaceholder")}
              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm outline-none transition-colors focus:border-primary"
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 flex items-center gap-1.5 font-medium">
              <Mail aria-hidden className="size-3.5 text-muted" />
              {t("email")}
            </span>
            <input
              required
              type="email"
              name="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm outline-none transition-colors focus:border-primary"
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 flex items-center gap-1.5 font-medium">
              <Lock aria-hidden className="size-3.5 text-muted" />
              {t("password")}
            </span>
            <span className="relative block">
              <input
                required
                type={showPassword ? "text" : "password"}
                name="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                className="w-full rounded-lg border border-border bg-background px-3 py-2.5 pr-11 text-sm outline-none transition-colors focus:border-primary"
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? t("hidePassword") : t("showPassword")}
                className="absolute right-1.5 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-md text-muted hover:bg-surface-2"
              >
                {showPassword ? (
                  <EyeOff aria-hidden className="size-4" />
                ) : (
                  <Eye aria-hidden className="size-4" />
                )}
              </button>
            </span>
          </label>
        </div>

        {error && (
          <p
            id="login-error"
            role="alert"
            className="mt-4 rounded-lg border border-st-urgent/30 bg-st-urgent/10 px-3 py-2 text-xs text-st-urgent"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className={clsx(
            "mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-contrast transition-colors hover:bg-primary-strong",
            submitting && "cursor-wait opacity-70",
          )}
        >
          {submitting ? t("submitting") : t("submit")}
          {!submitting && <ArrowRight aria-hidden className="size-4" />}
        </button>

        <div className="mt-5 flex items-center justify-between text-xs text-muted lg:hidden">
          <span>{t("demoHint")}</span>
          <button type="button" onClick={() => useDemo(0)} className="font-medium text-primary-strong">
            {t("admin")}
          </button>
        </div>
      </form>
    </div>
  );
}
