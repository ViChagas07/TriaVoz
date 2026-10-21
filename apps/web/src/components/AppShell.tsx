"use client";

import {
  Bot,
  CalendarDays,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  Phone,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useTransition, type ReactNode } from "react";
import { clsx } from "clsx";
import { LocaleSwitcher } from "./LocaleSwitcher";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";
import { initials } from "@/lib/format";
import type { User } from "@/lib/types";

type NavItem = {
  href: string;
  key: "dashboard" | "calls" | "appointments" | "agent" | "settings";
  icon: typeof Phone;
  adminOnly?: boolean;
};

const NAV: NavItem[] = [
  { href: "/painel", key: "dashboard", icon: LayoutDashboard },
  { href: "/chamadas", key: "calls", icon: Phone },
  { href: "/agendamentos", key: "appointments", icon: CalendarDays },
  { href: "/agente", key: "agent", icon: Bot, adminOnly: true },
  { href: "/configuracoes", key: "settings", icon: Settings, adminOnly: true },
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({
  children,
  user,
  clinicName,
  pending,
}: {
  children: ReactNode;
  user: User;
  clinicName: string;
  pending: number;
}) {
  const t = useTranslations("nav");
  const a11y = useTranslations("a11y");
  const pathname = usePathname();
  const router = useRouter();
  const [signingOut, startTransition] = useTransition();
  const isAdmin = user.role === "admin";
  const items = NAV.filter((item) => !item.adminOnly || isAdmin);

  function signOut() {
    startTransition(async () => {
      try {
        await fetch("/api/v1/auth/logout", { method: "POST", credentials: "same-origin" });
      } finally {
        router.replace("/login");
        router.refresh();
      }
    });
  }

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[16rem_1fr]">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-primary-contrast focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        {a11y("skip")}
      </a>

      <aside className="hidden border-r border-border bg-surface md:flex md:min-h-dvh md:flex-col">
        <div className="flex h-16 items-center border-b border-border px-5">
          <Logo />
        </div>
        <div className="px-3 py-4">
          <p className="px-2 pb-2 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-muted">
            {t("clinic")}
          </p>
          <p className="truncate px-2 text-sm font-medium" title={clinicName}>
            {clinicName}
          </p>
        </div>
        <nav aria-label={a11y("mainNav")} className="flex flex-1 flex-col gap-1 px-3">
          {items.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={clsx(
                  "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                  active
                    ? "bg-primary/10 font-medium text-primary-strong"
                    : "text-muted hover:bg-surface-2 hover:text-text",
                )}
              >
                <Icon aria-hidden className="size-4 shrink-0" />
                <span className="flex-1">{t(item.key)}</span>
                {item.key === "appointments" && pending > 0 && (
                  <span
                    className="rounded-full bg-primary px-2 py-0.5 text-[0.68rem] font-semibold text-primary-contrast"
                    aria-label={`${pending} ${t("pending")}`}
                  >
                    {pending > 99 ? "99+" : pending}
                  </span>
                )}
                {active && <ChevronRight aria-hidden className="size-3.5 opacity-60" />}
              </Link>
            );
          })}
        </nav>
        <div className="m-3 rounded-2xl border border-border bg-surface-2/60 p-3">
          <div className="flex items-center gap-2.5">
            <span className="grid size-9 shrink-0 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-contrast">
              {initials(user.full_name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user.full_name}</p>
              <p className="truncate text-xs text-muted">{user.email}</p>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between gap-1">
            <LocaleSwitcher />
            <ThemeToggle compact />
          </div>
          <button
            type="button"
            onClick={signOut}
            disabled={signingOut}
            className="mt-2 flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-muted transition-colors hover:bg-surface hover:text-text disabled:opacity-60"
          >
            <LogOut aria-hidden className="size-3.5" />
            {t("logout")}
          </button>
        </div>
      </aside>

      <div className="flex min-h-dvh flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-border bg-background/90 px-4 backdrop-blur md:hidden">
          <Logo />
          <div className="flex items-center gap-1.5">
            {pending > 0 && (
              <span
                className="rounded-full bg-primary px-2 py-0.5 text-[0.68rem] font-semibold text-primary-contrast"
                aria-label={`${pending} ${t("pending")}`}
              >
                {pending > 99 ? "99+" : pending}
              </span>
            )}
            <LocaleSwitcher />
            <ThemeToggle compact />
            <button
              type="button"
              onClick={signOut}
              disabled={signingOut}
              aria-label={t("logout")}
              className="grid size-8 place-items-center rounded-full border border-border text-muted"
            >
              <LogOut aria-hidden className="size-3.5" />
            </button>
          </div>
        </header>

        <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 pb-24 pt-5 sm:px-6 md:pb-10 md:pt-8">
          {children}
        </main>

        <nav
          aria-label={a11y("mainNav")}
          className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
        >
          <div className="mx-auto flex max-w-lg items-stretch justify-around">
            {items.map((item) => {
              const active = isActive(pathname, item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={clsx(
                    "flex flex-1 flex-col items-center gap-1 px-1 py-2.5 text-[0.68rem]",
                    active ? "font-medium text-primary-strong" : "text-muted",
                  )}
                >
                  <span className="relative">
                    <Icon aria-hidden className="size-5" />
                    {item.key === "appointments" && pending > 0 && (
                      <span className="absolute -right-2 -top-1 size-1.5 rounded-full bg-primary" />
                    )}
                  </span>
                  {t(item.key)}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}
