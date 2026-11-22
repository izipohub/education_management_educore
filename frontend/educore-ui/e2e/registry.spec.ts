import { expect, type Page, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: /Welcome/ })).toBeVisible();
}

test("a registry officer enrols their campus's admitted applicants", async ({ page }) => {
  await signIn(page, "registry-officer.whk");
  await page.getByRole("link", { name: "Enrolment" }).click();
  await expect(page.getByRole("heading", { name: "Enrolment", exact: true })).toBeVisible();

  const maria = page.getByRole("row").filter({ hasText: "Maria Kandjii" });
  await expect(maria).toBeVisible();
  await expect(maria.getByText("N$ 33,400.00")).toBeVisible();
  await expect(page.locator(".p-datatable-mask")).toHaveCount(0);
  await page.screenshot({ path: "e2e/results/registry-waiting.png", fullPage: true });

  // the dialog asks for the login email the applicant never gave (cancelled: demo data stays as it is)
  await maria.getByRole("button", { name: "Enrol" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel("Enrolled from")).toHaveValue("01-02-2027");
  await expect(dialog.getByRole("button", { name: "Enrol", exact: true })).toBeDisabled();
  await dialog.getByLabel("Student's email (their login)").fill("maria.kandjii@example.com");
  await expect(dialog.getByRole("button", { name: "Enrol", exact: true })).toBeEnabled();
  await page.screenshot({ path: "e2e/results/registry-dialog.png" });
  await dialog.getByRole("button", { name: "Cancel" }).click();
});

test("enrolled students show their fees", async ({ page }) => {
  await signIn(page, "registry-officer.whk");
  await page.getByRole("link", { name: "Enrolment" }).click();
  await page.getByRole("combobox", { name: "Academic year" }).click();
  await page.getByRole("option", { name: "2026" }).click();
  await page.getByText(/^Enrolled \(/).click();
  await expect(page.getByRole("row").filter({ hasText: "Ndapewa Amukoto" }).getByText("Paid")).toBeVisible();
  await expect(page.getByRole("row").filter({ hasText: "Lukas Garoeb" }).getByText(/Overdue: N\$ 35,500\.00 owing/)).toBeVisible();
});

test("admissions officers do not enrol", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await expect(page.getByRole("link", { name: "Enrolment" })).toHaveCount(0);
});
