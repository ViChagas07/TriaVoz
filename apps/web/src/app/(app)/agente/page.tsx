import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { AgentEditor } from "@/components/AgentEditor";
import { Card, PageHeader } from "@/components/Card";
import { DemoStage } from "@/components/DemoStage";
import { ScopedMessages } from "@/components/ScopedMessages";
import { getSession, serverApi } from "@/lib/server-api";
import type { AgentConfigState, ClinicSettings, ConfigVersion } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("agent");
  return { title: t("title") };
}

export default async function AgentPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.user.role !== "admin") redirect("/painel");
  const t = await getTranslations("agent");
  const [state, versions, limits] = await Promise.all([
    serverApi<AgentConfigState>("/agent-config"),
    serverApi<ConfigVersion[]>("/agent-config/versions"),
    serverApi<ClinicSettings>("/settings/clinic"),
  ]);

  return (
    <div className="space-y-5">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      <ScopedMessages
        namespaces={["agent", "common", "status", "errors", "theme"]}
        timeZone={limits.timezone}
      >
        <AgentEditor state={state} versions={versions} limits={limits} />
      </ScopedMessages>

      <Card className="p-5">
        <h2 className="text-sm font-semibold">{t("testTitle")}</h2>
        <p className="mt-1 text-xs text-muted">{t("testHint")}</p>
        <p className="mt-1 text-[0.68rem] text-st-pending">{t("testUsesPublished")}</p>
        <details className="mt-4 rounded-xl border border-border bg-surface-2/40 p-3">
          <summary className="cursor-pointer text-xs font-medium">{t("testTitle")}</summary>
          <div className="mt-4">
            <ScopedMessages
              namespaces={["demo", "common", "a11y", "status", "errors"]}
              timeZone={limits.timezone}
            >
              <DemoStage />
            </ScopedMessages>
          </div>
        </details>
      </Card>
    </div>
  );
}
