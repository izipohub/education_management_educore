import { expect, test } from "@playwright/test";
import { openRow, signIn, tableRow } from "./support";

test("the registrar sees the registration periods and rules", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Registration setup" }).click();
  await expect(page.getByRole("heading", { name: "Registration setup" })).toBeVisible();
  await expect(tableRow(page, "2027")).toBeVisible();

  await openRow(page, "2027", "Registration 2027");
  await expect(page.getByLabel("Closes")).toHaveValue("31-01-2027");
  await expect(page.getByLabel("Course changes until")).toHaveValue("28-02-2027");
  await page.screenshot({ path: "e2e/results/registration-period.png", fullPage: true });
  await page.getByRole("button", { name: "Cancel" }).click();

  await page.getByRole("tab", { name: "Settings" }).click();
  await expect(page.getByLabel("Most credits per year")).toBeVisible();
  await expect(page.getByLabel("Email students")).toBeChecked();
  await expect(page.getByRole("button", { name: "Save", exact: true })).toHaveCount(0); // nothing changed
  await page.screenshot({ path: "e2e/results/registration-settings.png", fullPage: true });
});
