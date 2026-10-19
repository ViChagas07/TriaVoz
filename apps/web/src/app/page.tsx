import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";

export default async function Landing() {
  const t = await getTranslations();
  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center gap-6 p-6">
      <div className="flex items-center justify-between">
        <span className="text-xl font-semibold text-primary">{t("brand.name")}</span>
        <LocaleSwitcher />
      </div>
      <h1 className="text-4xl font-bold tracking-tight">{t("landing.title")}</h1>
      <p className="text-lg text-muted">{t("landing.subtitle")}</p>
      <div className="flex gap-3">
        <Link
          href="/demo"
          className="rounded-lg bg-primary px-5 py-3 font-medium text-primary-contrast hover:bg-primary-strong"
        >
          {t("landing.cta")}
        </Link>
        <Link href="/login" className="rounded-lg border border-border px-5 py-3 font-medium">
          {t("nav.login")}
        </Link>
      </div>
      {/* TODO(P06): hero with voice visualizer, how-it-works, FAQ, JSON-LD, llms.txt, SEO/AEO/GEO */}
    </main>
  );
}
