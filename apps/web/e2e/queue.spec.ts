import { expect, test } from "@playwright/test";
import { createQueueItem, login, useEnglish } from "./helpers";

test.beforeEach(async ({ context }) => {
  await useEnglish(context);
});

test("login → queue → transcript → complete", async ({ page, request }) => {
  const item = await createQueueItem(request);
  await login(page);

  await page.goto("/agendamentos?tab=pending");
  await expect(page.getByRole("link", { name: item.title })).toBeVisible();

  await page.getByRole("link", { name: item.title }).first().click();
  const panel = page.getByRole("dialog");
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("heading", { name: item.title })).toBeVisible();

  await panel.getByRole("link", { name: "Call", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/chamadas/${item.callId}`));
  await expect(page.getByText(item.transcript)).toBeVisible();

  await page.goBack();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Complete" }).click();
  await expect(page.getByRole("dialog").getByText("Done")).toBeVisible();
  // The server refresh must drop the request from the pending table too, not only update the panel.
  await expect(page.getByRole("link", { name: item.title })).toHaveCount(0);

  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  await expect(page.getByRole("link", { name: item.title })).toHaveCount(0);
});
