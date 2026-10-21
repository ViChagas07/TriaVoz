import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Logo } from "./Logo";
import { LocaleSwitcher } from "./LocaleSwitcher";
import { ThemeToggle } from "./ThemeToggle";

export async function PublicHeader({ showLogin = true }: { showLogin?: boolean }) {
  const t = await getTranslations("nav");
  const a11y = await getTranslations("a11y");
  return (
    <header className="border-b border-border/80 bg-background/85 backdrop-blur">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-primary-contrast focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        {a11y("skip")}
      </a>
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <div className="flex items-center gap-2">
          <LocaleSwitcher />
          <ThemeToggle />
          {showLogin && (
            <Link
              href="/login"
              className="rounded-full border border-border bg-surface px-3.5 py-1.5 text-xs font-medium text-text transition-colors hover:border-primary/40 hover:text-primary-strong"
            >
              {t("login")}
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
