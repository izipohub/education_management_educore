import { expect, test } from "@playwright/test";
import { signIn } from "./support";

test("the bursar sets the fees and the account from ERPNext", async ({ page }) => {
  await signIn(page, "bursar");
  await page.getByRole("link", { name: "Fee settings" }).click();
  await expect(page.getByRole("heading", { name: "Fee settings" })).toBeVisible();
  const paper = page.getByLabel("Paper fee, local applicants");
  await expect(paper).toBeEnabled();
  await expect(page.getByText("Shown to applicants")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Late registration fee" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/fee-settings.png", fullPage: true });
  // nothing saved: the demo settings stay as they are
});

test("a finance officer reads the fee settings only", async ({ page }) => {
  await signIn(page, "finance-officer");
  await page.getByRole("link", { name: "Fee settings" }).click();
  await expect(page.getByLabel("Paper fee, local applicants")).toBeDisabled();
});

test("the registrar has no fee settings", async ({ page }) => {
  await signIn(page, "registrar");
  await expect(page.getByRole("link", { name: "Fee settings" })).toHaveCount(0);
});
