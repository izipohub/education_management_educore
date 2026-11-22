import { expect, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

test("anyone can see the open intake and the programmes, with their entry requirements", async ({ page }) => {
  await page.goto("/apply");
  await expect(page.getByRole("heading", { name: "2027 Intake" })).toBeVisible();
  const bcs = page.getByRole("article").filter({ hasText: "Bachelor of Computer Science" });
  await expect(bcs.getByText(/at least 25 points/)).toBeVisible();
  await expect(bcs.getByText(/Mathematics at least C \(NSSCO\)/)).toBeVisible();
  await page.screenshot({ path: "e2e/results/apply-landing.png", fullPage: true });
});

test("the registration form checks its fields before sending", async ({ page }) => {
  await page.goto("/apply/register");
  const create = page.getByRole("button", { name: "Create account" });
  await expect(create).toBeDisabled();
  await page.getByLabel("First name").fill("Test");
  await page.getByLabel("Last name").fill("Applicant");
  await page.getByLabel("Email").fill("not-an-email");
  await page.locator("#password").fill("Long-Passphrase-2027");
  await page.locator("#confirm").fill("Different-2027");
  await expect(page.getByText("The passwords are not the same.")).toBeVisible();
  await expect(create).toBeDisabled();
});

test("an applicant works through their draft application", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("applicant@educore.localhost");
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  // an applicant's home is their application
  await expect(page).toHaveURL(/\/application$/);
  await expect(page.getByRole("heading", { name: "Your application" })).toBeVisible();
  await expect(page.getByText("Draft: not submitted yet")).toBeVisible();
  await expect(page.getByText("✓ Complete: ready to submit")).toBeVisible();
  await expect(page.getByText(/Your points:\s*29/)).toBeVisible();
  await page.screenshot({ path: "e2e/results/application-about-you.png", fullPage: true });

  await page.getByText("2 · School and results").click();
  await expect(page.getByRole("combobox", { name: "Subject 1" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/application-results.png", fullPage: true });

  await page.getByText("3 · Programmes").click();
  await expect(page.getByText("Meets requirements").first()).toBeVisible();
  await expect(page.getByText("Biology below NSSCO C")).toBeVisible();
  await page.screenshot({ path: "e2e/results/application-choices.png", fullPage: true });

  await page.getByText("4 · Documents").click();
  await expect(page.getByText("National ID or Passport")).toBeVisible();
  await page.screenshot({ path: "e2e/results/application-documents.png", fullPage: true });

  // submitting needs the declaration (not submitted here: the demo draft stays a draft)
  await page.getByText("5 · Submit").click();
  const submit = page.getByRole("button", { name: "Submit application" });
  await expect(submit).toBeDisabled();
  await page.getByLabel(/I declare that the information/).check();
  await expect(submit).toBeEnabled();
  await page.screenshot({ path: "e2e/results/application-submit.png", fullPage: true });
});
