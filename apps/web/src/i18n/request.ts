import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

export const locales = ["pt-BR", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "pt-BR";

// Cookie-based locale for the base scaffold. TODO(P06): move to path-based routing for SEO/hreflang.
export default getRequestConfig(async () => {
  const cookieLocale = (await cookies()).get("locale")?.value;
  const locale: Locale = (locales as readonly string[]).includes(cookieLocale ?? "")
    ? (cookieLocale as Locale)
    : defaultLocale;
  return { locale, messages: (await import(`../../messages/${locale}.json`)).default };
});
