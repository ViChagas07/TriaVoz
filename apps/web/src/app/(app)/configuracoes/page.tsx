import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { Card, PageHeader } from "@/components/Card";
import { ScopedMessages } from "@/components/ScopedMessages";
import { SettingsClient } from "@/components/SettingsClient";
import { getSession, serverApi } from "@/lib/server-api";
import type {
  BlockedNumber,
  ClinicSettings,
  Professional,
  Service,
  TeamUser,
} from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("settings");
  return { title: t("title") };
}

type Tab = "clinic" | "services" | "professionals" | "blocked" | "team";

const TABS: { key: Tab; label: "tabsClinic" | "tabsServices" | "tabsProfessionals" | "tabsBlocked" | "tabsTeam" }[] = [
  { key: "clinic", label: "tabsClinic" },
  { key: "services", label: "tabsServices" },
  { key: "professionals", label: "tabsProfessionals" },
  { key: "blocked", label: "tabsBlocked" },
  { key: "team", label: "tabsTeam" },
];

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.user.role !== "admin") redirect("/painel");
  const t = await getTranslations("settings");
  const params = await searchParams;
  const tab = (
    typeof params.tab === "string" && TABS.some((item) => item.key === params.tab)
      ? params.tab
      : "clinic"
  ) as Tab;

  const [settings, services, professionals, blocked, team] = await Promise.all([
    serverApi<ClinicSettings>("/settings/clinic"),
    serverApi<Service[]>("/services"),
    serverApi<Professional[]>("/professionals"),
    serverApi<BlockedNumber[]>("/blocked-numbers").catch(() => []),
    serverApi<TeamUser[]>("/team").catch(() => []),
  ]);

  return (
    <div className="space-y-5">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      <nav
        aria-label={t("title")}
        className="flex gap-1 overflow-x-auto rounded-xl border border-border bg-surface p-1"
      >
        {TABS.map((item) => (
          <Link
            key={item.key}
            href={`/configuracoes?tab=${item.key}`}
            aria-current={tab === item.key ? "page" : undefined}
            className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
              tab === item.key
                ? "bg-primary/10 text-primary-strong"
                : "text-muted hover:bg-surface-2 hover:text-text"
            }`}
          >
            {t(item.label)}
          </Link>
        ))}
      </nav>

      <ScopedMessages
        namespaces={["settings", "common", "status", "errors"]}
        timeZone={settings.timezone}
      >
        <SettingsClient
          tab={tab}
          settings={settings}
          services={services}
          professionals={professionals}
          blocked={blocked}
          team={team}
          canManage={session.user.role === "admin"}
        />
      </ScopedMessages>
    </div>
  );
}
