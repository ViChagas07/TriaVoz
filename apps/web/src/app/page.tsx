import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import {
  ArrowRight,
  CalendarCheck2,
  Check,
  HeartHandshake,
  LockKeyhole,
  MessageSquareText,
  PhoneCall,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { PublicHeader } from "@/components/PublicHeader";
import { ScopedMessages } from "@/components/ScopedMessages";
import { VoiceOrb } from "@/components/VoiceOrb";
import { Logo } from "@/components/Logo";

const FAQ_KEYS = [1, 2, 3, 4] as const;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("landing");
  return {
    title: t("title"),
    description: t("subtitle"),
    alternates: { canonical: "/" },
    openGraph: { title: t("title"), description: t("subtitle"), url: "/" },
  };
}

export default async function Landing() {
  const t = await getTranslations("landing");
  const nav = await getTranslations("nav");
  const faqs = FAQ_KEYS.map((index) => ({
    question: t(`faq${index}Q` as "faq1Q"),
    answer: t(`faq${index}A` as "faq1A"),
  }));
  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: "TriaVoz",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      description: t("subtitle"),
      offers: { "@type": "Offer", price: "0", priceCurrency: "BRL" },
      featureList: [
        t("how2Title"),
        t("feature2Title"),
        t("feature3Title"),
      ],
      inLanguage: ["pt-BR", "en"],
    },
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: faqs.map((faq) => ({
        "@type": "Question",
        name: faq.question,
        acceptedAnswer: { "@type": "Answer", text: faq.answer },
      })),
    },
  ];

  return (
    <ScopedMessages namespaces={["landing", "nav", "common", "a11y", "theme"]}>
      <div className="min-h-dvh overflow-x-clip bg-[radial-gradient(circle_at_10%_-5%,color-mix(in_oklab,var(--voice)_16%,transparent),transparent_36%),radial-gradient(circle_at_95%_20%,color-mix(in_oklab,var(--primary)_13%,transparent),transparent_42%)]">
        <PublicHeader />

        <main id="main">
          <section className="mx-auto grid w-full max-w-6xl items-center gap-12 px-4 pb-16 pt-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:pb-24 lg:pt-20">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary-strong">
                <Sparkles aria-hidden className="size-3.5" />
                {t("eyebrow")}
              </p>
              <h1 className="text-balance mt-5 text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
                {t("title")}
              </h1>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-muted sm:text-lg">
                {t("subtitle")}
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/demo"
                  className="group inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition-colors hover:bg-primary-strong"
                >
                  <PhoneCall aria-hidden className="size-4" />
                  {t("ctaDemo")}
                  <ArrowRight
                    aria-hidden
                    className="size-4 transition-transform group-hover:translate-x-0.5"
                  />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-5 py-3 text-sm font-medium text-text transition-colors hover:border-primary/40 hover:text-primary-strong"
                >
                  {t("ctaLogin")}
                </Link>
              </div>
              <p className="mt-4 text-xs text-muted">{t("note")}</p>

              <ul className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted">
                <li className="inline-flex items-center gap-1.5">
                  <ShieldCheck aria-hidden className="size-3.5 text-primary-strong" />
                  {t("trusted")}
                </li>
                <li className="inline-flex items-center gap-1.5">
                  <LockKeyhole aria-hidden className="size-3.5 text-primary-strong" />
                  {t("trustedBody")}
                </li>
                <li className="inline-flex items-center gap-1.5">
                  <HeartHandshake aria-hidden className="size-3.5 text-primary-strong" />
                  SAMU 192
                </li>
              </ul>
            </div>

            <div className="relative mx-auto w-full max-w-md">
              <div className="absolute -inset-8 -z-10 rounded-full bg-voice/10 blur-3xl" aria-hidden />
              <div className="rounded-[2rem] border border-border bg-surface/90 p-6 shadow-card backdrop-blur sm:p-8">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-xs font-medium text-muted">
                    <span className="size-2 rounded-full bg-st-done" aria-hidden />
                    {t("liveLabel")}
                  </span>
                  <Logo compact />
                </div>
                <div className="mt-4 flex justify-center py-3">
                  <VoiceOrb state="listening" size="lg" label={t("how1Title")} />
                </div>
                <div className="mt-2 space-y-2">
                  <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-primary px-3.5 py-2 text-xs text-primary-contrast">
                    {t("demoLine1")}
                  </div>
                  <div className="max-w-[90%] rounded-2xl rounded-bl-md bg-surface-2 px-3.5 py-2 text-xs">
                    {t("demoLine2")}
                  </div>
                </div>
                <div className="mt-5 grid grid-cols-3 gap-2 text-center text-[0.65rem] text-muted">
                  <div className="rounded-lg bg-surface-2/70 px-2 py-2">
                    <CalendarCheck2 aria-hidden className="mx-auto mb-1 size-3.5 text-primary-strong" />
                    {t("how2Title")}
                  </div>
                  <div className="rounded-lg bg-surface-2/70 px-2 py-2">
                    <MessageSquareText aria-hidden className="mx-auto mb-1 size-3.5 text-primary-strong" />
                    {t("how3Title")}
                  </div>
                  <div className="rounded-lg bg-surface-2/70 px-2 py-2">
                    <ShieldCheck aria-hidden className="mx-auto mb-1 size-3.5 text-primary-strong" />
                    {t("feature2Title")}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="border-y border-border bg-surface/60">
            <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6 sm:py-20">
              <div className="max-w-2xl">
                <h2 className="text-balance text-2xl font-semibold tracking-tight sm:text-3xl">
                  {t("howTitle")}
                </h2>
                <p className="mt-2 text-sm text-muted">{t("howSubtitle")}</p>
              </div>
              <ol className="mt-8 grid gap-4 md:grid-cols-3">
                {[1, 2, 3].map((step) => (
                  <li key={step} className="rounded-2xl border border-border bg-surface p-5">
                    <span className="grid size-8 place-items-center rounded-full bg-primary-soft text-xs font-semibold text-primary-strong">
                      {step}
                    </span>
                    <h3 className="mt-4 text-sm font-semibold">
                      {t(`how${step}Title` as "how1Title")}
                    </h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted">
                      {t(`how${step}Body` as "how1Body")}
                    </p>
                  </li>
                ))}
              </ol>
            </div>
          </section>

          <section className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6 sm:py-20">
            <h2 className="text-balance text-2xl font-semibold tracking-tight sm:text-3xl">
              {t("featureTitle")}
            </h2>
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {[1, 2, 3].map((index) => (
                <div key={index} className="rounded-2xl border border-border bg-surface p-5">
                  <Check aria-hidden className="size-5 text-primary-strong" />
                  <h3 className="mt-4 text-sm font-semibold">
                    {t(`feature${index}Title` as "feature1Title")}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">
                    {t(`feature${index}Body` as "feature1Body")}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="border-t border-border bg-surface/60">
            <div className="mx-auto w-full max-w-4xl px-4 py-14 sm:px-6 sm:py-20">
              <h2 className="text-balance text-2xl font-semibold tracking-tight sm:text-3xl">
                {t("faqTitle")}
              </h2>
              <div className="mt-6 divide-y divide-border rounded-2xl border border-border bg-surface">
                {faqs.map((faq) => (
                  <details key={faq.question} className="group px-5 py-4">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-medium">
                      {faq.question}
                      <span
                        aria-hidden
                        className="text-muted transition-transform group-open:rotate-45"
                      >
                        +
                      </span>
                    </summary>
                    <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{faq.answer}</p>
                  </details>
                ))}
              </div>
            </div>
          </section>

          <section className="mx-auto w-full max-w-4xl px-4 py-14 text-center sm:px-6">
            <div className="rounded-3xl border border-primary/25 bg-primary/5 px-6 py-10">
              <h2 className="text-balance text-2xl font-semibold tracking-tight">{t("ctaDemo")}</h2>
              <p className="mx-auto mt-2 max-w-lg text-sm text-muted">{t("note")}</p>
              <div className="mt-6 flex flex-wrap justify-center gap-3">
                <Link
                  href="/demo"
                  className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast"
                >
                  <PhoneCall aria-hidden className="size-4" />
                  {nav("demo")}
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-5 py-3 text-sm font-medium"
                >
                  {t("ctaLogin")}
                </Link>
              </div>
            </div>
          </section>
        </main>

        <footer className="border-t border-border">
          <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-3 px-4 py-8 text-xs text-muted sm:flex-row sm:px-6">
            <Logo compact />
            <p>{t("footer")}</p>
            <p>{t("trustedBody")}</p>
          </div>
        </footer>
      </div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replaceAll("<", "\\u003c"),
        }}
      />
    </ScopedMessages>
  );
}
