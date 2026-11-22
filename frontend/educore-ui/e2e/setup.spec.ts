import { expect, type Page, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
}

test("the registrar sets the admission rules", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Admission setup" }).click();
  await expect(page.getByRole("heading", { name: "Admission setup" })).toBeVisible();

  // a rule changed and saved, then put back
  const days = page.getByLabel("Days to accept an offer");
  await expect(days).toHaveValue("14");
  const save = page.getByRole("button", { name: "Save", exact: true });
  await expect(save).toHaveCount(0); // nothing changed yet
  await days.fill("15");
  await days.blur();
  await save.click();
  await expect(page.getByText("Rules saved")).toBeVisible();
  await days.fill("14");
  await days.blur();
  await save.click();
  await expect(days).toHaveValue("14");
  await page.screenshot({ path: "e2e/results/setup-rules.png", fullPage: true });

  // pathways: one line each, details in the editor (closed without saving)
  await page.getByText("Pathways", { exact: true }).click();
  const mature = page.getByRole("row").filter({ hasText: "Mature age entry" });
  await expect(mature.getByText(/From age 23/)).toBeVisible();
  await mature.getByRole("button", { name: "Edit" }).click();
  await expect(page.getByLabel("Minimum age")).toHaveValue("23");
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));
  await page.screenshot({ path: "e2e/results/setup-pathway.png", fullPage: true });
  await page.getByRole("button", { name: "Cancel" }).click();

  await page.getByText("Programmes", { exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: "Master of Business Administration" }).getByText("NQF 7, 60%")).toBeVisible();

  await page.getByText("Points scale", { exact: true }).click();
  await expect(page.getByLabel("Grade 1", { exact: true })).toHaveValue("A*");
});

test("admissions officers do not see the setup", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await expect(page.getByRole("link", { name: "Admission setup" })).toHaveCount(0);
  await page.goto("/admission-setup");
  await expect(page).not.toHaveURL(/admission-setup/);
});
