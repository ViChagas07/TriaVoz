"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

const OPTIONS = [
  { value: "pt-BR", label: "pt-BR" },
  { value: "en", label: "en" },
] as const;

export function LocaleSwitcher({ className }: { className?: string }) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("a11y");
  const [pending, startTransition] = useTransition();

  return (
    <label
      className={`inline-flex cursor-pointer items-center ${className ?? ""}`}
    >
      <span className="sr-only">{t("language")}</span>
      <select
        aria-label={t("language")}
        value={locale}
        disabled={pending}
        onChange={(event) => {
          document.cookie = `locale=${event.target.value}; path=/; max-age=31536000; samesite=lax`;
          startTransition(() => router.refresh());
        }}
        className="cursor-pointer bg-transparent font-mono text-xs font-semibold text-muted outline-none transition-colors hover:text-primary-strong"
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
