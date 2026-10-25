"use client";

import { Eye, EyeOff } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";
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
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

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
    <div>
      <form
        onSubmit={onSubmit}
        method="post"
        data-hydrated={hydrated ? "true" : "false"}
        className="rounded-3xl border border-border bg-surface p-6 shadow-card sm:p-8"
        aria-describedby={error ? "login-error" : undefined}
      >
        <div className="mb-6">
          <h1 className="display-title text-2xl sm:text-[1.7rem]">{t("title")}</h1>
          <p className="mt-1.5 text-sm text-muted">{t("subtitle")}</p>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-1.5 block text-sm font-bold text-heading">{t("clinic")}</span>
            <input
              required
              name="clinic"
              value={clinic}
              onChange={(event) => setClinic(event.target.value)}
              autoComplete="organization"
              placeholder={t("clinicPlaceholder")}
              className="w-full rounded-lg border border-border bg-surface-2 px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-muted/60 focus:border-primary"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-sm font-bold text-heading">{t("email")}</span>
            <input
              required
              type="email"
              name="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              placeholder="voce@clinica.com"
              className="w-full rounded-lg border border-border bg-surface-2 px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-muted/60 focus:border-primary"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-sm font-bold text-heading">{t("password")}</span>
            <span className="relative block">
              <input
                required
                type={showPassword ? "text" : "password"}
                name="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full rounded-lg border border-border bg-surface-2 px-3.5 py-2.5 pr-11 text-sm outline-none transition-colors focus:border-primary"
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? t("hidePassword") : t("showPassword")}
                className="absolute right-1.5 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text"
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
          disabled={submitting || !hydrated}
          className={clsx(
            "mt-6 flex w-full items-center justify-center rounded-lg bg-primary px-4 py-3 text-sm font-bold text-primary-contrast transition-colors hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-60",
            submitting && "cursor-wait",
          )}
        >
          {submitting ? t("submitting") : t("submit")}
        </button>
      </form>

      <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
        <span className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-muted">
          {t("demoHint")}
        </span>
        {DEMO_ACCOUNTS.map((account, index) => (
          <button
            key={account.key}
            type="button"
            onClick={() => useDemo(index)}
            className="rounded-full border border-border bg-surface px-3 py-1.5 font-mono text-[0.65rem] text-muted transition-colors hover:border-primary/40 hover:text-primary-strong"
          >
            {account.email}
          </button>
        ))}
      </div>
    </div>
  );
}
