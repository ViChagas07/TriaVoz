import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { DemoStage } from "@/components/DemoStage";
import { PublicHeader } from "@/components/PublicHeader";
import { ScopedMessages } from "@/components/ScopedMessages";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("demo");
  return {
    title: t("title"),
    description: t("subtitle"),
    alternates: { canonical: "/demo" },
  };
}

export default async function DemoPage({
  searchParams,
}: {
  searchParams: Promise<{ preview?: string | string[] }>;
}) {
  const t = await getTranslations("demo");
  const params = await searchParams;
  const preview =
    process.env.NODE_ENV !== "production" && typeof params.preview === "string"
      ? params.preview
      : undefined;

  return (
    <ScopedMessages namespaces={["demo", "common", "a11y", "theme", "nav", "errors"]}>
      <div className="min-h-dvh">
        <PublicHeader showNav={false} showLogin={false} dashboardCta />
        <main id="main" className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
          <header className="mb-8 max-w-2xl">
            <p className="eyebrow">{t("eyebrow")}</p>
            <h1 className="display-title text-balance mt-2 text-3xl sm:text-4xl">{t("title")}</h1>
            <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">{t("subtitle")}</p>
          </header>
          <DemoStage preview={preview} />
          <p className="mt-6 max-w-3xl font-mono text-[0.68rem] leading-relaxed text-muted">
            {t("recordingNotice")} {t("disclaimer")}
          </p>
        </main>
      </div>
    </ScopedMessages>
  );
}
