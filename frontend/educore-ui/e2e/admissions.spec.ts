import { expect, test } from "@playwright/test";
import { listItem, openRecord, pane, signIn } from "./support";

test("an admissions officer sees their campus's applications, with decisions they may take", async ({ page }) => {
  await signIn(page, "admissions-officer.osh");
  await expect(page.getByText(/^Oshakati Campus · /)).toBeVisible();

  await page.getByRole("link", { name: "Admissions" }).click();
  await expect(page.getByRole("heading", { name: "Admissions", exact: true })).toBeVisible();
  await expect(listItem(page, "Hilma Nakale")).toBeVisible();
  await expect(listItem(page, "Elias Haimbodi")).toBeVisible();
  // Windhoek's applicants are not this officer's
  await expect(listItem(page, "Selma Nghifikwa")).toHaveCount(0);

  // a paper application can be decided at once
  await openRecord(page, "Hilma Nakale");
  await expect(pane(page).getByRole("button", { name: "Make offer" })).toBeEnabled();
  await page.screenshot({ path: "e2e/results/admissions-officer-osh.png" });

  // rejecting asks for a reason first (cancelled: the demo data stays as it is)
  await pane(page).getByRole("button", { name: "Reject", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Reject", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "Cancel" }).click();

  // ↓ moves to the next application
  await listItem(page, "Hilma Nakale").click();
  await page.keyboard.press("ArrowDown");
  await expect(pane(page).getByRole("heading", { name: "Elias Haimbodi" })).toBeVisible();
});

test("the registrar sees every campus, and a full offering", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Admissions" }).click();
  await expect(listItem(page, "Selma Nghifikwa")).toBeVisible();
  await expect(listItem(page, "Rosalia Fredericks")).toBeVisible();
  // BSAMS-WHK-FT: 2 places, both offered, so Johannes cannot be offered one
  await openRecord(page, "Johannes Swartbooi");
  await expect(pane(page).getByText("2 of 2 offered")).toBeVisible();
  await expect(pane(page).getByRole("button", { name: "Make offer" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/registrar.png" });
});

test("staff without admissions rights have no Admissions screen", async ({ page }) => {
  await signIn(page, "registry-officer.osh");
  await expect(page.getByRole("link", { name: "Admissions" })).toHaveCount(0);
  await page.goto("/admissions");
  await expect(page.getByRole("heading", { name: /^Good (morning|afternoon|evening)/ })).toBeVisible();
});
