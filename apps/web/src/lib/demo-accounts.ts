// DEV/DEMO ONLY. These match apps/api/scripts/seed_demo.py. If the public demo is ever made
// private, remove this file and the chips: credentials must not ship in a client bundle (P09).
export const DEMO_PASSWORD = "Demo!TriaVoz2026";

export type DemoAccount = {
  key: string;
  labelKey: "admin" | "attendant";
  clinic: string;
  email: string;
};

export const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    key: "admin",
    labelKey: "admin",
    clinic: "clinica-horizonte",
    email: "admin@horizonte.demo",
  },
  {
    key: "attendant",
    labelKey: "attendant",
    clinic: "clinica-horizonte",
    email: "recepcao@horizonte.demo",
  },
];
