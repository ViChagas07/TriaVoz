import { expect, test } from "@playwright/test";
import { login, useEnglish } from "./helpers";

test.beforeEach(async ({ context }) => {
  await useEnglish(context);
});

test("agent config edit → publish → rollback", async ({ page }) => {
  await login(page);
  await page.goto("/agente");

  const suffix = Date.now().toString(36);
  const clinicName = `Clinica Horizonte ${suffix}`;
  await page.getByRole("textbox", { name: "Clinic name", exact: true }).fill(clinicName);
  await expect(page.getByText("You have unpublished changes.")).toBeVisible();

  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(page.getByRole("status")).toContainText("Draft saved.");

  await page.getByRole("button", { name: "Publish version" }).click();
  await expect(page.getByRole("status")).toContainText("Version published.");

  const restore = page.getByRole("button", { name: "Restore" }).first();
  await expect(restore).toBeVisible();
  await restore.click();
  await expect(page.getByRole("status")).toContainText("Version restored.");
});
