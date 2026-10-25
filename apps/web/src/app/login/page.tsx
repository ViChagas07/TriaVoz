import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { LoginForm } from "@/components/LoginForm";
import { PublicHeader } from "@/components/PublicHeader";
import { ScopedMessages } from "@/components/ScopedMessages";
import { getSession } from "@/lib/server-api";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("auth");
  return { title: t("title"), robots: { index: false, follow: false } };
}

function safeNext(value: string | string[] | undefined): string {
  if (typeof value !== "string") return "/painel";
  // Only a single-slash, same-origin path is allowed. Backslashes, encoded slashes and control
  // characters are rejected so a crafted `?next=` cannot become an open redirect.
  if (!value.startsWith("/") || value.startsWith("//")) return "/painel";
  if (value.includes("\\") || /[\u0000-\u001f\u007f]/.test(value)) return "/painel";
  try {
    const resolved = new URL(value, "https://triavoice.invalid");
    if (resolved.origin !== "https://triavoice.invalid") return "/painel";
    if (!resolved.pathname.startsWith("/") || resolved.pathname.startsWith("//")) {
      return "/painel";
    }
    return `${resolved.pathname}${resolved.search}${resolved.hash}`;
  } catch {
    return "/painel";
  }
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
      <div className="min-h-dvh">
        <PublicHeader showNav={false} showLogin={false} />
        <main
          id="main"
          className="mx-auto flex min-h-[calc(100dvh-4rem)] w-full max-w-md flex-col justify-center px-4 py-10 sm:px-6"
        >
          <LoginForm nextPath={safeNext(params.next)} />
        </main>
      </div>
    </ScopedMessages>
  );
}
