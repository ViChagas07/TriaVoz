import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { LocaleSwitcher } from "./LocaleSwitcher";

const NAV = [
  { href: "/painel", key: "dashboard" },
  { href: "/solicitacoes", key: "requests" },
  { href: "/agenda", key: "agenda" },
  { href: "/historico", key: "history" },
  { href: "/chamadas", key: "calls" },
  { href: "/agente", key: "agent" }, // TODO(P06): admin-only
  { href: "/equipe", key: "team" }, // TODO(P06): admin-only
  { href: "/configuracoes", key: "settings" },
] as const;

export async function AppShell({ children }: { children: React.ReactNode }) {
  const t = await getTranslations();
  return (
    <div className="min-h-dvh md:grid md:grid-cols-[15rem_1fr]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:rounded focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-contrast"
      >
        {t("a11y.skip")}
      </a>
      <aside className="border-b border-border bg-surface p-4 md:border-b-0 md:border-r">
        <div className="mb-4 flex items-center justify-between md:mb-6">
          <span className="text-lg font-semibold text-primary">{t("brand.name")}</span>
          <LocaleSwitcher />
        </div>
        <nav aria-label="principal" className="flex flex-wrap gap-1 md:flex-col">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-2 text-sm text-text hover:bg-primary/10 hover:text-primary-strong"
            >
              {t(`nav.${item.key}`)}
            </Link>
          ))}
        </nav>
      </aside>
      <main id="main" className="p-6">
        {children}
      </main>
    </div>
  );
}
