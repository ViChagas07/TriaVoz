import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { LoginForm } from "@/components/LoginForm";
import { PublicHeader } from "@/components/PublicHeader";
import { ScopedMessages } from "@/components/ScopedMessages";
import { getSession } from "@/lib/server-api";
import { Logo } from "@/components/Logo";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("auth");
  return { title: t("title"), robots: { index: false, follow: false } };
}

function safeNext(value: string | string[] | undefined): string {
  if (typeof value !== "string") return "/painel";
  if (!value.startsWith("/") || value.startsWith("//")) return "/painel";
  return value;
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const session = await getSession();
  if (session) redirect("/painel");
  const params = await searchParams;

  return (
    <ScopedMessages namespaces={["auth", "common", "errors", "nav", "a11y", "theme"]}>
      <div className="min-h-dvh bg-[radial-gradient(circle_at_20%_0%,color-mix(in_oklab,var(--voice)_16%,transparent),transparent_40%),radial-gradient(circle_at_90%_100%,color-mix(in_oklab,var(--primary)_12%,transparent),transparent_45%)]">
        <PublicHeader showLogin={false} />
        <main id="main" className="mx-auto flex min-h-[calc(100dvh-4rem)] w-full max-w-6xl flex-col justify-center px-4 py-10 sm:px-6">
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <LoginForm nextPath={safeNext(params.next)} />
        </main>
      </div>
    </ScopedMessages>
  );
}
