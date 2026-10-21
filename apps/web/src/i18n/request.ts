import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { defaultLocale, locales, loadMessages, type Locale } from "./messages";

export { defaultLocale, locales };
export type { Locale };

// Cookie-based locale keeps the URL surface at the nine product routes. hreflang points at
// `?lang=pt-BR|en`; middleware persists that into the cookie and redirects to the clean URL.
export default getRequestConfig(async () => {
  const cookieLocale = (await cookies()).get("locale")?.value;
  const locale: Locale = (locales as readonly string[]).includes(cookieLocale ?? "")
    ? (cookieLocale as Locale)
    : defaultLocale;
  return { locale, messages: await loadMessages(locale) };
});
