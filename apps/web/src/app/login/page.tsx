import { getTranslations } from "next-intl/server";

export default async function LoginPage() {
  const t = await getTranslations("login");
  // TODO(P03/P06): wire to POST /api/v1/auth/login (clinic code + email + password).
  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <label className="grid gap-1 text-sm">
        {t("clinic")}
        <input className="rounded-md border border-border bg-surface px-3 py-2" name="clinic" autoComplete="organization" />
      </label>
      <label className="grid gap-1 text-sm">
        {t("email")}
        <input className="rounded-md border border-border bg-surface px-3 py-2" name="email" type="email" autoComplete="username" />
      </label>
      <label className="grid gap-1 text-sm">
        {t("password")}
        <input className="rounded-md border border-border bg-surface px-3 py-2" name="password" type="password" autoComplete="current-password" />
      </label>
      <button className="rounded-lg bg-primary px-4 py-2 font-medium text-primary-contrast" type="button">
        {t("submit")}
      </button>
    </main>
  );
}
