import { getTranslations } from "next-intl/server";

type NavKey = "dashboard" | "requests" | "agenda" | "history" | "calls" | "agent" | "team" | "settings";

/** Temporary page body. Each page is replaced by its real implementation in prompt P06. */
export async function PagePlaceholder({ titleKey, hint }: { titleKey: NavKey; hint?: string }) {
  const t = await getTranslations();
  return (
    <section>
      <h1 className="text-2xl font-semibold">{t(`nav.${titleKey}`)}</h1>
      <p className="mt-2 text-sm text-muted">
        {t("placeholder.todo")}
        {hint ? ` · ${hint}` : ""}
      </p>
    </section>
  );
}
