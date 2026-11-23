import { expect, test } from "@playwright/test";
import { signIn } from "./support";

test("the registrar's dashboard leads to the work waiting", async ({ page }) => {
  await signIn(page, "registrar");
  await expect(page.getByRole("heading", { name: /^Good (morning|afternoon|evening), Registrar/ })).toBeVisible();
  const decide = page.locator(".stat").filter({ hasText: "Applications to decide" });
  await expect(decide.getByText(/^\d+$/)).toBeVisible();
  // the full offering is named in words, not by colour
  await expect(page.getByRole("row").filter({ hasText: "BSAMS-WHK-FT" }).getByText("Full")).toBeVisible();
  // the oldest applications waiting open their own page
  await expect(page.getByRole("heading", { name: "Awaiting a decision" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/dashboard-registrar.png", fullPage: true });

  await decide.getByRole("link", { name: /Review/ }).click();
  await expect(page.getByRole("heading", { name: "Admissions", exact: true })).toBeVisible();
});

test("the bursar sees student fees collected per campus", async ({ page }) => {
  await signIn(page, "bursar");
  await expect(page.getByRole("heading", { name: /Student fees \d{4}/ })).toBeVisible();
  await expect(page.getByRole("list", { name: "Fees collected against invoiced, per campus" }).getByRole("listitem")).toHaveCount(3);
  // nothing of admissions for finance
  await expect(page.getByText("Applications to decide")).toHaveCount(0);
});
