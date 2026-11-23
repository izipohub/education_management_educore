import { expect, test } from "@playwright/test";
import { openRow, record, signIn, tableRow } from "./support";

test("an admissions officer sees their campus's applications, with decisions they may take", async ({ page }) => {
  await signIn(page, "admissions-officer.osh");
  await expect(page.getByText(/^Oshakati Campus · /)).toBeVisible();

  await page.getByRole("link", { name: "Admissions" }).click();
  await expect(page.getByRole("heading", { name: "Admissions", exact: true })).toBeVisible();
  await expect(tableRow(page, "Hilma Nakale")).toBeVisible();
  await expect(tableRow(page, "Elias Haimbodi")).toBeVisible();
  // Windhoek's applicants are not this officer's
  await expect(tableRow(page, "Selma Nghifikwa")).toHaveCount(0);

  // a paper application can be decided at once, on its own page
  await openRow(page, "Hilma Nakale");
  await expect(record(page).getByRole("button", { name: "Make offer" })).toBeEnabled();
  await page.screenshot({ path: "e2e/results/admissions-officer-osh.png" });

  // rejecting asks for a reason first (cancelled: the demo data stays as it is)
  await record(page).getByRole("button", { name: "Reject", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Reject", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "Cancel" }).click();

  // back to the same list
  await page.getByRole("link", { name: "Admissions", exact: true }).first().click();
  await expect(tableRow(page, "Elias Haimbodi")).toBeVisible();
});

test("the registrar sees every campus, and a full offering", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Admissions" }).click();
  await expect(tableRow(page, "Selma Nghifikwa")).toBeVisible();
  await expect(tableRow(page, "Rosalia Fredericks")).toBeVisible();
  // BSAMS-WHK-FT: 2 places, both offered, so Johannes cannot be offered one
  await openRow(page, "Johannes Swartbooi");
  await expect(record(page).getByText("2 of 2 · Full")).toBeVisible();
  await expect(record(page).getByRole("button", { name: "Make offer" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/registrar.png" });
});

test("staff without admissions rights have no Admissions screen", async ({ page }) => {
  await signIn(page, "registry-officer.osh");
  await expect(page.getByRole("link", { name: "Admissions" })).toHaveCount(0);
  await page.goto("/admissions");
  await expect(page.getByRole("heading", { name: /^Good (morning|afternoon|evening)/ })).toBeVisible();
});

test("an admissions officer types in a paper application", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await page.getByRole("link", { name: "Admissions" }).click();
  await page.getByRole("button", { name: "New paper application" }).click();
  await expect(page.getByRole("heading", { name: "New paper application", level: 1 })).toBeVisible({ timeout: 15_000 });
  const capture = page.getByRole("button", { name: "Capture application" });
  await expect(capture).toBeDisabled();
  await expect(page.getByText("Email to fill in").filter({ visible: true })).toBeVisible();

  await page.getByLabel("First name(s)").fill("Paper");
  await page.getByLabel("Surname", { exact: true }).fill("Applicant");
  await page.getByLabel("Date of birth").fill("14-03-2007");
  await page.getByLabel("Date of birth").press("Escape");
  await page.locator("#email").fill("paper.applicant@example.com");
  // the phone keeps its country code (Namibia first)
  await page.locator("#d-mobile").fill("081 123 4567");
  await expect(page.getByRole("combobox", { name: "Country code for d-mobile" })).toContainText("+264");
  await page.locator("#choice-0").click();
  await page.getByRole("option", { name: /Bachelor of Computer Science · Windhoek/ }).click();
  // the paper fee, paid at the cashier
  await expect(page.getByText("Application fee N$ 200.00")).toBeVisible();
  await expect(capture).toBeEnabled();
  await page.screenshot({ path: "e2e/results/capture-paper.png", fullPage: true });
  // not captured: the demo data stays as it is
});
