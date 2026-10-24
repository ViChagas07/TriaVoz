import { expect, test } from "@playwright/test";
import { API_URL, createCall, login, useEnglish, WEB_URL } from "./helpers";

test.beforeEach(async ({ context }) => {
  await useEnglish(context);
});

test("a clinic A user cannot open clinic B's call URLs", async ({ page, request }) => {
  const own = await createCall(request);
  const foreign = await createCall(request, {
    email: "admin@vida-leve.demo",
    clinic: "clinica-vida-leve",
  });

  await login(page);

  const ownResponse = await page.goto(`/chamadas/${own.callId}`);
  expect(ownResponse?.status()).toBe(200);
  await expect(page.getByText(own.transcript)).toBeVisible();

  const foreignResponse = await page.goto(`/chamadas/${foreign.callId}`);
  // Next may stream a 200 shell before `notFound()`; the UI must still be the not-found page.
  expect([200, 404]).toContain(foreignResponse?.status());
  await expect(page.getByText("Page not found")).toBeVisible();
  await expect(page.getByText(foreign.transcript)).toHaveCount(0);

  const access = (await page.context().cookies(WEB_URL)).find(
    (cookie) => cookie.name === "triavoz_access",
  )?.value;
  expect(access).toBeTruthy();
  const apiResponse = await request.get(`${API_URL}/api/v1/calls/${foreign.callId}`, {
    headers: { Cookie: `triavoz_access=${access}` },
  });
  expect(apiResponse.status()).toBe(404);
});
