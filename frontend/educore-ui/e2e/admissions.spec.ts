import { expect, type Page, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: /Welcome/ })).toBeVisible();
}

test("an admissions officer sees their campus's applications, with decisions they may take", async ({ page }) => {
  await signIn(page, "admissions-officer.osh");
  await expect(page.getByText("Oshakati Campus")).toBeVisible();

  await page.getByRole("link", { name: "Admissions" }).click();
  await expect(page.getByRole("heading", { name: "Admissions", exact: true })).toBeVisible();

  await expect(page.getByText("Hilma Nakale")).toBeVisible();
  await expect(page.getByText("Elias Haimbodi")).toBeVisible();
  // Windhoek's applicants are not this officer's
  await expect(page.getByText("Selma Nghifikwa")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Approve", exact: true })).toHaveCount(2);
  await expect(page.locator(".p-datatable-mask")).toHaveCount(0);
  await page.screenshot({ path: "e2e/results/admissions-officer-osh.png", fullPage: true });

  // rejecting asks for a reason first (cancelled: the demo data stays as it is)
  await page.getByRole("button", { name: "Reject", exact: true }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("button", { name: "Reject", exact: true })).toBeDisabled();
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});

test("the registrar sees every campus, and a full offering", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Admissions" }).click();
  await expect(page.getByText("Selma Nghifikwa")).toBeVisible();
  await expect(page.getByText("Rosalia Fredericks")).toBeVisible();
  // BSAMS-WHK-FT: 2 places, both offered, so Johannes cannot be approved
  await expect(page.getByText("2 of 2")).toBeVisible();
  const johannes = page.getByRole("row").filter({ hasText: "Johannes Swartbooi" });
  await expect(johannes.getByRole("button", { name: "Approve", exact: true })).toBeDisabled();
  await expect(page.locator(".p-datatable-mask")).toHaveCount(0);
  await page.screenshot({ path: "e2e/results/registrar.png", fullPage: true });
});

test("staff without admissions rights have no Admissions screen", async ({ page }) => {
  await signIn(page, "registry-officer.osh");
  await expect(page.getByRole("link", { name: "Admissions" })).toHaveCount(0);
  await page.goto("/admissions");
  await expect(page.getByRole("heading", { name: /Welcome/ })).toBeVisible();
});
