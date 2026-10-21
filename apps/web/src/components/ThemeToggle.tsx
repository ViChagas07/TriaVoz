"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { clsx } from "clsx";

type Theme = "light" | "dark" | "system";

function apply(theme: Theme) {
  const root = document.documentElement;
  if (theme === "system") {
    delete root.dataset.theme;
    window.localStorage.removeItem("triavoz-theme");
  } else {
    root.dataset.theme = theme;
    window.localStorage.setItem("triavoz-theme", theme);
  }
}

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const t = useTranslations("theme");
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    const stored = window.localStorage.getItem("triavoz-theme");
    setTheme(stored === "light" || stored === "dark" ? stored : "system");
  }, []);

  const options: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: "light", label: t("light"), icon: Sun },
    { value: "dark", label: t("dark"), icon: Moon },
    { value: "system", label: t("system"), icon: Monitor },
  ];

  return (
    <div
      className={clsx(
        "inline-flex items-center gap-0.5 rounded-full border border-border bg-surface/80 p-1",
        compact && "rounded-lg",
      )}
      role="group"
      aria-label={t("toggle")}
    >
      {options.map((option) => {
        const Icon = option.icon;
        const active = theme === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => {
              setTheme(option.value);
              apply(option.value);
            }}
            aria-pressed={active}
            title={option.label}
            className={clsx(
              "grid size-7 place-items-center rounded-full text-muted transition-colors",
              active && "bg-primary/10 text-primary-strong",
              "hover:bg-primary/10 hover:text-primary-strong",
            )}
          >
            <Icon aria-hidden className="size-3.5" />
            <span className="sr-only">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
