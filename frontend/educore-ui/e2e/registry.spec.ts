import { expect, test } from "@playwright/test";
import { openRow, record, signIn, tableRow } from "./support";

test("a registry officer enrols their campus's admitted applicants", async ({ page }) => {
  await signIn(page, "registry-officer.whk");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Registration", exact: true })).toBeVisible();

  await openRow(page, "Maria Kandjii");
  await expect(record(page).getByText("N$ 33,400.00")).toBeVisible();
  // the login is the email on the application: nothing to type (not registered: demo data stays as it is)
  await expect(record(page).getByLabel("Registered from")).toHaveValue("01-02-2027");
  await expect(record(page).getByText("maria.kandjii@educore.localhost").first()).toBeVisible();
  await expect(record(page).getByLabel("Student's email (their login)")).toHaveCount(0);
  await expect(record(page).getByRole("button", { name: "Register", exact: true })).toBeEnabled();
  await page.screenshot({ path: "e2e/results/registry-waiting.png" });
});

test("enrolled students show their fees", async ({ page }) => {
  await signIn(page, "registry-officer.whk");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  await page.getByRole("combobox", { name: "Academic year" }).click();
  await page.getByRole("option", { name: "2026", exact: true }).click();
  await page.getByRole("tab", { name: /^Registered/ }).click();
  await expect(tableRow(page, "Ndapewa Amukoto").getByText("Paid")).toBeVisible();
  await openRow(page, "Lukas Garoeb");
  await expect(record(page).locator("dt").filter({ hasText: /^Owing$/ }).locator("xpath=following-sibling::dd[1]")).toHaveText("N$ 35,500.00");
  await expect(record(page).getByRole("heading", { name: "Fees" })).toBeVisible();
});

test("admissions officers do not enrol", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await expect(page.getByRole("link", { name: "Registration", exact: true })).toHaveCount(0);
});
