import { AppShell } from "@/components/AppShell";

// TODO(P03/P06): require an authenticated session here (redirect to /login) and enforce roles.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
