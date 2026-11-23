import { expect, type Page, test } from "@playwright/test";
import { tableRow } from "./support";

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
  await expect(page.getByText("Settings saved")).toBeVisible();
  await days.fill("14");
  await days.blur();
  await save.click();
  await expect(days).toHaveValue("14");
  // the fees are shown, set by Finance
  await expect(page.getByText("Set by Finance").first()).toBeVisible();
  await expect(page.getByText("N$ 200.00")).toBeVisible();
  await expect(page.getByText("Applicants pay into")).toBeVisible();
  await page.screenshot({ path: "e2e/results/setup-rules.png", fullPage: true });

  // pathways: a list, each on its own page (nothing saved)
  await page.getByRole("tab", { name: /^Entry pathways/ }).click();
  await expect(tableRow(page, "Mature Age Entry").getByText(/from age 25/)).toBeVisible();
  await tableRow(page, "Mature Age Entry").getByRole("link", { name: "Mature Age Entry" }).click();
  await expect(page.getByLabel("Minimum age")).toHaveValue("25");
  // the name can be changed; renaming keeps its applications (cancelled here)
  await page.getByLabel("Name", { exact: true }).fill("Mature Age Entry (MAE)");
  await expect(page.getByText("Renaming keeps its applications")).toBeVisible();
  await page.screenshot({ path: "e2e/results/setup-pathway.png" });
  await page.getByRole("button", { name: "Cancel" }).click();
  // back on the same list
  await expect(page).toHaveURL(/tab=pathways/);
  await expect(tableRow(page, "Mature Age Entry")).toBeVisible();

  await page.getByRole("tab", { name: /^Programmes/ }).click();
  await expect(tableRow(page, "Master of Business Administration").getByText(/NQF 7, 60%/)).toBeVisible();

  await page.getByRole("tab", { name: "Admission point scale" }).click();
  await expect(page.getByLabel("Grade 1", { exact: true })).toHaveValue("A*");
});

test("admissions officers do not see the setup", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await expect(page.getByRole("link", { name: "Admission setup" })).toHaveCount(0);
  await page.goto("/admission-setup");
  await expect(page).not.toHaveURL(/admission-setup/);
});
