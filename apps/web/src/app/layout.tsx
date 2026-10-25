import type { Metadata } from "next";
import { Archivo, Inter, JetBrains_Mono } from "next/font/google";
import { headers } from "next/headers";
import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";
import { ThemeScript } from "@/components/ThemeScript";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const archivo = Archivo({
  subsets: ["latin"],
  variable: "--font-archivo",
  display: "swap",
});

const jetmono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetmono",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3300";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "TriaVoice — recepção por voz com IA para clínicas",
    template: "%s · TriaVoice",
  },
  description:
    "Agente de voz com IA que atende a clínica, consulta horários reais, marca, remarca e cancela consultas, registra tudo e passa para uma pessoa quando precisa.",
  applicationName: "TriaVoice",
  authors: [{ name: "TriaVoice" }],
  creator: "TriaVoice",
  keywords: [
    "agente de voz",
    "recepção com IA",
    "clínica",
    "agendamento por voz",
    "voice AI",
    "clinic receptionist",
  ],
  alternates: {
    canonical: "/",
    languages: {
      "pt-BR": "/?lang=pt-BR",
      en: "/?lang=en",
    },
  },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    alternateLocale: ["en_US"],
    url: siteUrl,
    siteName: "TriaVoice",
    title: "TriaVoice — recepção por voz com IA",
    description:
      "Atende, entende e agenda por voz. Consulta a agenda real, registra a conversa e entrega para um humano quando precisa.",
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "TriaVoice" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "TriaVoice — recepção por voz com IA",
    description: "Atende, entende e agenda por voz com dados reais da clínica.",
    images: ["/opengraph-image"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
  manifest: "/manifest.webmanifest",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return (
    <html
      lang={locale}
      suppressHydrationWarning
      className={`${inter.variable} ${archivo.variable} ${jetmono.variable}`}
    >
      <head>
        <ThemeScript nonce={nonce} />
      </head>
      <body className="min-h-dvh bg-background font-sans text-text antialiased">
        {children}
      </body>
    </html>
  );
}
