import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import {
  ArrowRight,
  AudioLines,
  CalendarX2,
  ChevronDown,
  Database,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Zap,
} from "lucide-react";
import { DashboardPreview } from "@/components/DashboardPreview";
import { Logo } from "@/components/Logo";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { PublicHeader } from "@/components/PublicHeader";
import { ScopedMessages } from "@/components/ScopedMessages";
import { ThemeToggle } from "@/components/ThemeToggle";

const REPO_URL = "https://github.com/ViChagas07/TriaVoz";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("landing");
  const title = `${t("title")} ${t("titleGrad")}`;
  return {
    title,
    description: t("subtitle"),
    alternates: { canonical: "/" },
    openGraph: { title, description: t("subtitle"), url: "/" },
  };
}

export default async function Landing() {
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  const t = await getTranslations("landing");
  const nav = await getTranslations("nav");
  const faqs = [1, 2, 3, 4, 5, 6].map((index) => ({
    question: t(`faq${index}Q` as "faq1Q"),
    answer: t(`faq${index}A` as "faq1A"),
  }));
  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: "TriaVoice",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      description: t("subtitle"),
      offers: { "@type": "Offer", price: "0", priceCurrency: "BRL" },
      featureList: [t("sec1Title"), t("sec2Title"), t("sec3Title"), t("sec4Title")],
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

  const stack = ["LiveKit", "Deepgram", "Claude", "ElevenLabs", "FastAPI", "PostgreSQL RLS", "Next.js"];
  const steps = [1, 2, 3].map((step) => ({
    number: `0${step}`,
    title: t(`step${step}Title` as "step1Title"),
    body: t(`step${step}Body` as "step1Body"),
  }));
  const STEP_ICONS = [AudioLines, Sparkles, Database];
  const guards = [1, 2, 3, 4].map((index) => ({
    title: t(`sec${index}Title` as "sec1Title"),
    body: t(`sec${index}Body` as "sec1Body"),
  }));
  const GUARD_ICONS = [Zap, CalendarX2, ShieldCheck, SlidersHorizontal];
  const archNodes = [1, 2, 3, 4, 5].map((index) => ({
    name: t(`arch${index}Name` as "arch1Name"),
    sub: t(`arch${index}Sub` as "arch1Sub"),
  }));
  const stats = [
    { value: "< 1 s", label: t("stat1Label") },
    { value: "0", label: t("stat2Label") },
    { value: "100%", label: t("stat3Label") },
  ];

  return (
    <ScopedMessages namespaces={["landing", "nav", "common", "a11y", "theme"]}>
      <div className="min-h-dvh overflow-x-clip">
        <PublicHeader />

        <main id="main">
          {/* Hero */}
          <section className="mx-auto grid w-full max-w-6xl items-center gap-10 px-4 pb-16 pt-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:pb-24 lg:pt-20">
            <div>
              <p className="inline-block rounded-md border border-primary/15 bg-primary/5 px-2.5 py-1">
                <span className="eyebrow">{t("eyebrow")}</span>
              </p>
              <h1 className="display-title text-balance mt-5 text-4xl leading-[1.04] sm:text-5xl lg:text-[3.6rem]">
                {t("title")}{" "}
                <span className="text-grad">{t("titleGrad")}</span>
              </h1>
              <p className="mt-5 max-w-xl text-base leading-relaxed text-muted">
                {t("subtitle")}
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/demo"
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast transition-colors hover:bg-primary-strong"
                >
                  {t("ctaDemo")}
                  <ArrowRight aria-hidden className="size-4" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-5 py-3 text-sm font-semibold text-heading transition-colors hover:border-primary/40 hover:text-primary-strong"
                >
                  {t("ctaPanel")}
                </Link>
              </div>
              <p className="mt-4 font-mono text-[0.68rem] text-muted">{t("note")}</p>
            </div>

            <div className="relative mx-auto flex w-full max-w-md items-center justify-center py-10">
              <div
                aria-hidden
                className="absolute inset-0 rounded-full bg-[radial-gradient(circle,color-mix(in_oklab,var(--orb-b)_24%,transparent),transparent_66%)] blur-2xl"
              />
              <div className="orb relative size-80 sm:size-96">
                <span className="orb-halo" aria-hidden />
                <span className="orb-halo-2" aria-hidden />
                <span className="hero-orb size-[64%]" aria-hidden />
              </div>
              <span className="float-pill absolute left-0 top-16 rounded-full border border-border bg-surface px-3 py-1.5 font-mono text-[0.65rem] text-muted shadow-card sm:left-2">
                {t("pillChecking")}
              </span>
              <span
                className="float-pill absolute bottom-10 left-2 rounded-full border border-border bg-surface px-3 py-1.5 font-mono text-[0.65rem] text-muted shadow-card sm:left-8"
                style={{ animationDelay: "-2.2s" }}
              >
                {t("pillLatency")}
              </span>
              <span
                className="float-pill absolute right-0 top-24 rounded-full border border-border bg-surface px-3 py-1.5 font-mono text-[0.65rem] text-muted shadow-card sm:-right-2"
                style={{ animationDelay: "-4.1s" }}
              >
                {t("pillConfirmed")}
              </span>
            </div>
          </section>

          {/* Built with */}
          <section className="border-y border-border bg-surface/60">
            <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-4 sm:px-6">
              <span className="eyebrow">{t("stackLabel")}</span>
              {stack.map((item) => (
                <span key={item} className="text-[0.8rem] font-medium text-muted">
                  {item}
                </span>
              ))}
            </div>
          </section>

          {/* How it works */}
          <section id="como-funciona" className="mx-auto w-full max-w-6xl scroll-mt-20 px-4 py-14 sm:px-6 sm:py-20">
            <p className="eyebrow">{t("howEyebrow")}</p>
            <h2 className="display-title text-balance mt-3 text-3xl sm:text-4xl">
              {t("howTitle")}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
              {t("howSubtitle")}
            </p>
            <ol className="mt-10 grid gap-5 md:grid-cols-3">
              {steps.map((step, index) => {
                const Icon = STEP_ICONS[index] ?? Sparkles;
                return (
                  <li
                    key={step.title}
                    className="relative rounded-2xl border border-border bg-surface p-6"
                  >
                    {index > 0 && (
                      <span
                        aria-hidden
                        className="absolute -left-[26px] top-1/2 z-10 hidden size-8 -translate-y-1/2 place-items-center rounded-full border border-border bg-background text-muted md:grid"
                      >
                        <ArrowRight className="size-3.5" />
                      </span>
                    )}
                    <div className="flex items-start justify-between">
                      <span className="grid size-11 place-items-center rounded-xl bg-[linear-gradient(135deg,color-mix(in_oklab,var(--grad-a)_18%,transparent),color-mix(in_oklab,var(--grad-b)_16%,transparent))] text-primary-strong">
                        <Icon aria-hidden className="size-5" />
                      </span>
                      <span className="font-mono text-xs text-muted">{step.number}</span>
                    </div>
                    <h3 className="display-title mt-5 text-lg">{step.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted">{step.body}</p>
                  </li>
                );
              })}
            </ol>
          </section>

          {/* Product in action */}
          <section id="produto" className="mx-auto w-full max-w-6xl scroll-mt-20 px-4 py-10 sm:px-6 sm:py-14">
            <p className="eyebrow">{t("productEyebrow")}</p>
            <h2 className="display-title text-balance mt-3 max-w-xl text-3xl sm:text-4xl">
              {t("productTitle")}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
              {t("productSubtitle")}
            </p>
            <div className="mt-10">
              <DashboardPreview t={(key) => t(key as "previewLive")} />
            </div>
          </section>

          {/* Built like production */}
          <section id="seguranca" className="mx-auto w-full max-w-6xl scroll-mt-20 px-4 py-14 sm:px-6 sm:py-20">
            <p className="eyebrow">{t("securityEyebrow")}</p>
            <h2 className="display-title text-balance mt-3 text-3xl sm:text-4xl">
              {t("securityTitle")}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
              {t("securitySubtitle")}
            </p>
            <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {guards.map((guard, index) => {
                const Icon = GUARD_ICONS[index] ?? ShieldCheck;
                return (
                  <div key={guard.title} className="rounded-2xl border border-border bg-surface p-6">
                    <Icon aria-hidden className="size-5 text-primary-strong" />
                    <h3 className="mt-4 text-sm font-bold text-heading">{guard.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted">{guard.body}</p>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Illustrative numbers */}
          <section className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
            <div
              className="rounded-3xl px-6 py-10 sm:px-12"
              style={{ background: "var(--navy)" }}
            >
              <p className="font-mono text-[0.72rem] font-bold uppercase tracking-[0.22em] text-white/55">
                {t("statsLabel")}
              </p>
              <dl className="mt-6 grid gap-8 sm:grid-cols-3">
                {stats.map((stat) => (
                  <div key={stat.label}>
                    <dt className="sr-only">{stat.label}</dt>
                    <dd>
                      <span
                        className="block font-mono text-4xl font-bold sm:text-5xl"
                        style={{ color: "var(--grad-a)" }}
                      >
                        {stat.value}
                      </span>
                      <span className="mt-2 block text-sm text-white/65">{stat.label}</span>
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          </section>

          {/* Architecture */}
          <section id="arquitetura" className="mx-auto w-full max-w-6xl scroll-mt-20 px-4 py-14 sm:px-6 sm:py-20">
            <p className="eyebrow">{t("archEyebrow")}</p>
            <h2 className="display-title text-balance mt-3 max-w-lg text-3xl sm:text-4xl">
              {t("archTitle")}
            </h2>
            <div className="mt-10 rounded-3xl border border-border bg-surface p-6 sm:p-10">
              <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">
                {archNodes.map((node, index) => (
                  <div key={node.name} className="flex flex-1 flex-col items-center lg:flex-row">
                    {index > 0 && (
                      <ArrowRight
                        aria-hidden
                        className="mb-2 size-4 shrink-0 rotate-90 text-muted lg:mb-0 lg:mr-3 lg:rotate-0"
                      />
                    )}
                    <div
                      className={`w-full flex-1 rounded-2xl border bg-surface px-4 py-4 text-center ${
                        index % 2 === 0
                          ? "border-[color-mix(in_oklab,var(--grad-a)_55%,transparent)]"
                          : "border-[color-mix(in_oklab,var(--grad-b)_55%,transparent)]"
                      }`}
                    >
                      <p className="text-sm font-bold text-heading">{node.name}</p>
                      <p className="mt-0.5 font-mono text-[0.62rem] text-muted">{node.sub}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-6 flex flex-col items-center gap-1">
                <svg
                  viewBox="0 0 200 24"
                  className="h-6 w-44 text-muted"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M10 2 C 60 22, 140 22, 190 2"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeDasharray="4 5"
                    strokeLinecap="round"
                  />
                </svg>
                <p className="font-mono text-[0.65rem] text-muted">{t("archDash")}</p>
              </div>
            </div>
          </section>

          {/* FAQ */}
          <section id="faq" className="mx-auto w-full max-w-4xl scroll-mt-20 px-4 py-14 sm:px-6 sm:py-20">
            <p className="eyebrow">{t("faqEyebrow")}</p>
            <h2 className="display-title text-balance mt-3 max-w-lg text-3xl sm:text-4xl">
              {t("faqTitle")}
            </h2>
            <div className="mt-10 space-y-3">
              {faqs.map((faq) => (
                <details
                  key={faq.question}
                  className="group rounded-xl border border-border bg-surface px-5 py-4"
                >
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-bold text-heading">
                    {faq.question}
                    <ChevronDown
                      aria-hidden
                      className="size-4 shrink-0 text-muted transition-transform group-open:rotate-180"
                    />
                  </summary>
                  <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{faq.answer}</p>
                </details>
              ))}
            </div>
          </section>

          {/* CTA band */}
          <section className="mx-auto w-full max-w-6xl px-4 pb-16 pt-4 sm:px-6 sm:pb-20">
            <div
              className="flex flex-col gap-6 rounded-3xl px-6 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-12"
              style={{ background: "var(--band-bg)" }}
            >
              <div>
                <p
                  className="font-mono text-[0.72rem] font-bold uppercase tracking-[0.22em]"
                  style={{ color: "var(--band-eyebrow)" }}
                >
                  {t("ctaEyebrow")}
                </p>
                <h2
                  className="display-title mt-2 max-w-md text-2xl sm:text-3xl"
                  style={{ color: "var(--band-heading)" }}
                >
                  {t("ctaTitle")}
                </h2>
              </div>
              <Link
                href="/demo"
                className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg px-5 py-3 text-sm font-semibold transition-colors sm:self-center"
                style={{
                  background: "var(--band-btn-bg)",
                  color: "var(--band-btn-text)",
                }}
              >
                {t("ctaButton")}
                <ArrowRight aria-hidden className="size-4" />
              </Link>
            </div>
          </section>
        </main>

        <footer className="border-t border-border">
          <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row sm:px-6">
            <Logo />
            <p className="text-center text-xs text-muted">{t("footerCredit")}</p>
            <div className="flex items-center gap-2">
              <a
                href={REPO_URL}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center rounded-full px-2 py-1.5 text-xs font-semibold text-muted transition-colors hover:text-primary-strong"
              >
                GitHub
              </a>
              <LocaleSwitcher />
              <ThemeToggle />
            </div>
          </div>
        </footer>
      </div>
      <script
        type="application/ld+json"
        nonce={nonce}
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replaceAll("<", "\\u003c"),
        }}
      />
    </ScopedMessages>
  );
}
