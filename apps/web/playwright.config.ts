import { defineConfig } from "@playwright/test";
import path from "node:path";

const baseURL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:3300";
const apiURL = process.env.E2E_API_URL ?? "http://127.0.0.1:58000";

function env(overrides: Record<string, string | undefined>): Record<string, string> {
  return Object.fromEntries(
    Object.entries({ ...process.env, ...overrides }).filter(
      (entry): entry is [string, string] => typeof entry[1] === "string",
    ),
  );
}

const appDsn = process.env.TRIAVOZ_TEST_APP_DSN ?? "postgresql://triavoz_app@127.0.0.1:55433/triavoz";
const asyncAppDsn = appDsn.replace(/^postgresql:\/\//, "postgresql+asyncpg://");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  outputDir: "test-results",
  use: {
    baseURL,
    trace: "on",
    video: "on",
    screenshot: "only-on-failure",
    locale: "en-US",
    navigationTimeout: 60_000,
    actionTimeout: 20_000,
  },
  webServer: [
    {
      command: "poetry run uvicorn triavoz.main:app --host 127.0.0.1 --port 58000 --log-level warning",
      cwd: path.resolve(process.cwd(), "../api"),
      url: `${apiURL}/health`,
      timeout: 180_000,
      reuseExistingServer: !process.env.CI,
      env: env({
        TRIAVOZ_DATABASE_URL_APP: asyncAppDsn,
        TRIAVOZ_REDIS_URL: process.env.TRIAVOZ_TEST_REDIS_URL ?? "redis://127.0.0.1:6379/15",
        TRIAVOZ_JWT_SECRET:
          process.env.TRIAVOZ_JWT_SECRET ?? "e2e-jwt-secret-0123456789abcdef0123456789abcdef",
        TRIAVOZ_INTERNAL_HMAC_SECRET:
          process.env.TRIAVOZ_INTERNAL_HMAC_SECRET ??
          "e2e-hmac-secret-0123456789abcdef0123456789abcdef",
        TRIAVOZ_DEMO_CLINIC_SLUG: "clinica-horizonte",
        TRIAVOZ_COOKIE_SECURE: "false",
        TRIAVOZ_LOG_FORMAT: "plain",
        TRIAVOZ_METRICS_ENABLED: "false",
      }),
    },
    {
      command: "npm run build && npm run start -- --hostname 127.0.0.1 --port 3300",
      cwd: process.cwd(),
      url: `${baseURL}/login`,
      timeout: 300_000,
      reuseExistingServer: !process.env.CI,
      env: env({
        API_ORIGIN: apiURL,
        NEXT_PUBLIC_SITE_URL: baseURL,
        NEXT_PUBLIC_TRIAVOZ_E2E: "1",
        NEXT_TELEMETRY_DISABLED: "1",
      }),
    },
  ],
});
