"use client";

import { Moon, Sun } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { clsx } from "clsx";

type Effective = "light" | "dark";

function readEffective(): Effective {
  const explicit = document.documentElement.dataset.theme;
  if (explicit === "dark") return "dark";
  if (explicit === "light") return "light";
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

/** Single-icon toggle: follows the system until an explicit choice is stored. */
export function ThemeToggle({ className }: { className?: string }) {
  const t = useTranslations("theme");
  const [effective, setEffective] = useState<Effective>("light");

  useEffect(() => {
    setEffective(readEffective());
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (!document.documentElement.dataset.theme) setEffective(readEffective());
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const toggle = useCallback(() => {
    const next: Effective = readEffective() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      window.localStorage.setItem("triavoz-theme", next);
    } catch {
      /* private mode */
    }
    setEffective(next);
  }, []);

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={t("toggle")}
      title={t("toggle")}
      className={clsx(
        "grid size-8 shrink-0 place-items-center rounded-full text-muted transition-colors hover:bg-primary/10 hover:text-primary-strong",
        className,
      )}
    >
      {effective === "dark" ? (
        <Moon aria-hidden className="size-4" />
      ) : (
        <Sun aria-hidden className="size-4" />
      )}
    </button>
  );
}
