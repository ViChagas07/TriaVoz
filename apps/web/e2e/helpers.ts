import { createHmac, randomBytes } from "node:crypto";
import { expect, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";

export const API_URL = process.env.E2E_API_URL ?? "http://127.0.0.1:58000";
export const WEB_URL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:3300";
export const DEMO_PASSWORD = "Demo!TriaVoz2026";
const HMAC_SECRET =
  process.env.TRIAVOZ_INTERNAL_HMAC_SECRET ??
  "e2e-hmac-secret-0123456789abcdef0123456789abcdef";

export async function useEnglish(context: BrowserContext): Promise<void> {
  await context.addCookies([{ name: "locale", value: "en", url: WEB_URL }]);
}

export async function login(
  page: Page,
  email = "admin@horizonte.demo",
  clinic = "clinica-horizonte",
): Promise<void> {
  await page.goto("/login");
  await page.locator('form[data-hydrated="true"]').waitFor();
  await page.locator('input[name="clinic"]').fill(clinic);
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/painel/);
}

async function apiLogin(
  request: APIRequestContext,
  email: string,
  clinic: string,
): Promise<string> {
  const response = await request.post(`${API_URL}/api/v1/auth/login`, {
    data: { clinic_code: clinic, email, password: DEMO_PASSWORD },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

async function clinicOf(request: APIRequestContext, token: string): Promise<string> {
  const response = await request.get(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return ((await response.json()) as { clinic_id: string }).clinic_id;
}

async function internalPost(
  request: APIRequestContext,
  path: string,
  body: Record<string, unknown>,
): Promise<unknown> {
  const raw = JSON.stringify(body);
  const timestamp = Math.floor(Date.now() / 1000);
  const nonce = randomBytes(16).toString("hex");
  const signature = createHmac("sha256", HMAC_SECRET)
    .update(`${timestamp}.${nonce}.`)
    .update(raw)
    .digest("hex");
  const response = await request.post(`${API_URL}/internal/agent${path}`, {
    data: raw,
    headers: {
      "Content-Type": "application/json",
      "X-Triavoz-Timestamp": String(timestamp),
      "X-Triavoz-Nonce": nonce,
      "X-Triavoz-Signature": signature,
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

export type CallItem = {
  transcript: string;
  callId: string;
};

export type QueueItem = CallItem & {
  title: string;
  requestId: string;
};

export async function createCall(
  request: APIRequestContext,
  {
    email = "admin@horizonte.demo",
    clinic = "clinica-horizonte",
  }: { email?: string; clinic?: string } = {},
): Promise<CallItem> {
  const token = await apiLogin(request, email, clinic);
  const clinicId = await clinicOf(request, token);
  const suffix = `${Date.now()}-${randomBytes(3).toString("hex")}`;
  const phone = `+5571999${Math.floor(100000 + Math.random() * 899999)}`;
  const transcript = `E2E transcript ${suffix}`;

  const call = (await internalPost(request, "/calls/start", {
    clinic_id: clinicId,
    channel: "web",
    caller_number: phone,
  })) as { call_id: string };
  await internalPost(request, "/calls/turns", {
    clinic_id: clinicId,
    call_id: call.call_id,
    turns: [
      { seq: 0, speaker: "patient", content: transcript },
      { seq: 1, speaker: "agent", content: "I will register your request." },
    ],
  });
  return { callId: call.call_id, transcript };
}

export async function createQueueItem(
  request: APIRequestContext,
  options: { email?: string; clinic?: string } = {},
): Promise<QueueItem> {
  const token = await apiLogin(
    request,
    options.email ?? "admin@horizonte.demo",
    options.clinic ?? "clinica-horizonte",
  );
  const clinicId = await clinicOf(request, token);
  const call = await createCall(request, options);
  const title = `E2E exam result ${Date.now()}-${randomBytes(3).toString("hex")}`;
  const created = (await internalPost(request, "/tools/create-service-request", {
    clinic_id: clinicId,
    call_id: call.callId,
    type: "message",
    title,
    description: "Synthetic QA request",
    patient_name: "QA Patient",
  })) as { request_id: string };

  return { ...call, title, requestId: created.request_id };
}
