import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("the registrar sets up funding routes and what each asks for", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Admission setup", exact: true }).click();
  await page.getByRole("tab", { name: /^Funding routes/ }).click();
  await expect(tableRow(page, "NSFAF")).toContainText("None");
  await expect(tableRow(page, "Employer")).toContainText("Pays");
  await page.screenshot({ path: "e2e/results/funding-routes.png", fullPage: true });

  await tableRow(page, "NSFAF").getByRole("link", { name: "NSFAF" }).click();
  await expect(page.getByText("No application fee").first()).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Document 1", exact: true })).toContainText("NSFAF award or application letter");
  await page.screenshot({ path: "e2e/results/funding-route.png", fullPage: true });
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("tab", { name: /^Funding routes/ })).toHaveAttribute("aria-selected", "true");
});

test("the bursar sets the regional fee and the routes that pay no application fee", async ({ page }) => {
  await signIn(page, "bursar");
  await page.getByRole("link", { name: "Fee settings", exact: true }).click();
  await expect(page.getByRole("row", { name: /Regional applicants/ })).toBeVisible();
  await expect(page.getByText("Their citizens pay the regional fee (15)")).toBeVisible();
  const free = page.locator("#fee-free").locator("xpath=ancestor::*[contains(@class,'p-multiselect')][1]");
  await expect(free).toContainText("NSFAF");
  await expect(free).toContainText("NTA");
  await page.screenshot({ path: "e2e/results/fee-settings-funding.png", fullPage: true });
});

test("financial aid sees students who named NSFAF on their application", async ({ page }) => {
  await signIn(page, "financial-aid-officer");
  await page.getByRole("link", { name: "Sponsors", exact: true }).click();
  await tableRow(page, "Namibia Students Financial Assistance Fund").getByRole("link").first().click();
  await expect(record(page).getByRole("heading", { name: "Named on their application" })).toBeVisible();
  const row = record(page).getByRole("row").filter({ hasText: "Ndapewa Amukoto" });
  await row.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByLabel("Student", { exact: true })).toHaveValue(/Ndapewa Amukoto/);
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});
