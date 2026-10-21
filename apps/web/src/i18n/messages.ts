import type { AbstractIntlMessages } from "next-intl";

export const locales = ["pt-BR", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "pt-BR";

const loaders = {
  "pt-BR": () => import("../../messages/pt-BR.json"),
  en: () => import("../../messages/en.json"),
} as const;

export async function loadMessages(locale: string): Promise<Record<string, unknown>> {
  const loader = loaders[(locale as Locale) in loaders ? (locale as Locale) : defaultLocale];
  return (await loader()).default as Record<string, unknown>;
}

/** Only send the namespaces a route's client islands actually use to the browser. */
export function pickMessages(
  all: Record<string, unknown>,
  namespaces: readonly string[],
): AbstractIntlMessages {
  const picked: Record<string, unknown> = {};
  for (const namespace of namespaces) {
    if (all[namespace] !== undefined) picked[namespace] = all[namespace];
  }
  return picked as AbstractIntlMessages;
}
