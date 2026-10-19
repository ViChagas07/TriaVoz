"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";

const OPTIONS = [
  { value: "pt-BR", label: "Português" },
  { value: "en", label: "English" },
];

export function LocaleSwitcher() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("a11y");
  return (
    <select
      aria-label={t("language")}
      value={locale}
      onChange={(e) => {
        document.cookie = `locale=${e.target.value}; path=/; max-age=31536000; samesite=lax`;
        router.refresh();
      }}
      className="rounded-md border border-border bg-surface px-2 py-1 text-sm text-text"
    >
      {OPTIONS.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
