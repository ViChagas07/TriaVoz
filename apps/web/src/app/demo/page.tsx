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
      <div className="min-h-dvh bg-[radial-gradient(circle_at_15%_-10%,color-mix(in_oklab,var(--voice)_14%,transparent),transparent_38%),radial-gradient(circle_at_100%_100%,color-mix(in_oklab,var(--primary)_12%,transparent),transparent_42%)]">
        <PublicHeader />
        <main id="main" className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
          <header className="mb-6 max-w-2xl">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-primary-strong">
              {t("eyebrow")}
            </p>
            <h1 className="mt-2 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              {t("title")}
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted">{t("subtitle")}</p>
          </header>
          <DemoStage preview={preview} />
          <p className="mt-6 max-w-3xl text-xs leading-relaxed text-muted">
            {t("recordingNotice")} {t("disclaimer")}
          </p>
        </main>
      </div>
    </ScopedMessages>
  );
}
