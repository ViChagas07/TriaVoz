import { NextIntlClientProvider } from "next-intl";
import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";
import { loadMessages, pickMessages } from "@/i18n/messages";

type Props = {
  namespaces: readonly string[];
  children: ReactNode;
  timeZone?: string;
};

/** Scoped client provider: a route only ships the message groups it renders. */
export async function ScopedMessages({ namespaces, children, timeZone }: Props) {
  const locale = await getLocale();
  const all = await loadMessages(locale);
  return (
    <NextIntlClientProvider
      locale={locale}
      messages={pickMessages(all, namespaces)}
      timeZone={timeZone}
    >
      {children}
    </NextIntlClientProvider>
  );
}
