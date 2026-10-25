import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { LayoutDashboard, Menu } from "lucide-react";
import { Logo } from "./Logo";
import { LocaleSwitcher } from "./LocaleSwitcher";
import { ThemeToggle } from "./ThemeToggle";

const ANCHORS = [
  { href: "/#como-funciona", key: "how" },
  { href: "/#seguranca", key: "security" },
  { href: "/#arquitetura", key: "architecture" },
  { href: "/#faq", key: "faq" },
] as const;

const LINK_CLASS =
  "text-[0.82rem] font-semibold text-navlink transition-colors hover:text-primary-strong";

export async function PublicHeader({
  showNav = true,
  showLogin = true,
  dashboardCta = false,
}: {
  showNav?: boolean;
  showLogin?: boolean;
  dashboardCta?: boolean;
}) {
  const t = await getTranslations("nav");
  const a11y = await getTranslations("a11y");
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-primary-contrast focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        {a11y("skip")}
      </a>
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <div className="flex items-center gap-2 sm:gap-3">
          {showNav && (
            <nav aria-label={a11y("mainNav")} className="hidden items-center gap-6 md:flex">
              {ANCHORS.map((anchor) => (
                <Link key={anchor.href} href={anchor.href} className={LINK_CLASS}>
                  {t(anchor.key)}
                </Link>
              ))}
              <Link href="/demo" className={LINK_CLASS}>
                {t("demo")}
              </Link>
              {showLogin && (
                <Link href="/login" className={LINK_CLASS}>
                  {t("login")}
                </Link>
              )}
            </nav>
          )}
          {dashboardCta && (
            <Link
              href="/painel"
              className="inline-flex items-center gap-1.5 text-[0.82rem] font-semibold text-primary transition-colors hover:text-primary-strong"
            >
              <LayoutDashboard aria-hidden className="size-4" />
              {t("dashboardCta")}
            </Link>
          )}
          <LocaleSwitcher />
          <ThemeToggle />
          {showNav && (
            <details className="relative md:hidden">
              <summary
                aria-label={t("openMenu")}
                className="grid size-8 cursor-pointer list-none place-items-center rounded-full text-muted transition-colors hover:bg-primary/10 hover:text-primary-strong"
              >
                <Menu aria-hidden className="size-4.5" />
              </summary>
              <div className="panel-in absolute right-0 top-10 z-50 w-48 rounded-2xl border border-border bg-surface p-2 shadow-card">
                {ANCHORS.map((anchor) => (
                  <Link
                    key={anchor.href}
                    href={anchor.href}
                    className="block rounded-lg px-3 py-2 text-sm text-text hover:bg-surface-2"
                  >
                    {t(anchor.key)}
                  </Link>
                ))}
                <Link
                  href="/demo"
                  className="block rounded-lg px-3 py-2 text-sm text-text hover:bg-surface-2"
                >
                  {t("demo")}
                </Link>
                {showLogin && (
                  <Link
                    href="/login"
                    className="block rounded-lg px-3 py-2 text-sm text-text hover:bg-surface-2"
                  >
                    {t("login")}
                  </Link>
                )}
              </div>
            </details>
          )}
        </div>
      </div>
    </header>
  );
}
