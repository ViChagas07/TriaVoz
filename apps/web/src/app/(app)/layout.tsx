import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import { ScopedMessages } from "@/components/ScopedMessages";
import { getSession, serverApi } from "@/lib/server-api";
import type { ClinicSettings, Dashboard } from "@/lib/types";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const me = await getSession();
  if (!me) redirect("/login");

  const [settingsResult, dashboardResult] = await Promise.allSettled([
    serverApi<ClinicSettings>("/settings/clinic"),
    serverApi<Dashboard>("/dashboard"),
  ]);

  const clinicName =
    settingsResult.status === "fulfilled" ? settingsResult.value.name : "TriaVoz";
  const pending =
    dashboardResult.status === "fulfilled" ? dashboardResult.value.pending_requests : 0;

  return (
    <ScopedMessages
      namespaces={["nav", "a11y", "theme", "common", "status", "errors"]}
      timeZone={settingsResult.status === "fulfilled" ? settingsResult.value.timezone : undefined}
    >
      <AppShell user={me.user} clinicName={clinicName} pending={pending}>
        {children}
      </AppShell>
    </ScopedMessages>
  );
}
