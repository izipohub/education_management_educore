import { expect, type Page, test } from "@playwright/test";
import { openRow, record as recordPage } from "./support";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
}

test("a mature age applicant enters work experience instead of school results", async ({ page }) => {
  await signIn(page, "mature.applicant");
  await expect(page.getByText("Pathway: Mature age entry")).toBeVisible();
  // documents still missing; no points: they are not judged on school results
  await expect(page.getByText("Document: Proof of Employment")).toBeVisible();
  await expect(page.getByText(/Your points/)).toHaveCount(0);

  await page.getByText("2 · Work experience").click();
  await expect(page.getByRole("heading", { name: /Your work experience/ })).toBeVisible();
  // saved jobs are one line each; Edit opens the form
  await expect(page.getByText(/Store Manager, Demo Retail Group/)).toBeVisible();
  await expect(page.getByLabel("Employer")).toHaveCount(0);
  await page.getByRole("button", { name: "Edit job 1" }).click();
  await expect(page.getByLabel("Employer")).toHaveValue("Demo Retail Group");
  await expect(page.getByLabel("Secondary school")).toHaveCount(0);
  await page.screenshot({ path: "e2e/results/pathway-mature-work.png", fullPage: true });

  // only undergraduate programmes are offered on an undergraduate route
  await page.getByText("3 · Programmes").click();
  await expect(page.getByText("Review", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Entry: at least/)).toHaveCount(0);
  await page.getByRole("combobox", { name: "Choice 3" }).click();
  await expect(page.getByRole("option", { name: /Bachelor of Accounting/ }).first()).toBeVisible();
  await expect(page.getByRole("option", { name: /Master of Business Administration/ })).toHaveCount(0);
  await page.keyboard.press("Escape");

  // changing to a postgraduate route warns before the choices go (not saved: the demo draft stays as it is)
  await page.getByText("1 · About you").click();
  await page.getByRole("combobox", { name: "Pathway" }).click();
  await page.getByRole("option", { name: "Postgraduate" }).click();
  await expect(page.getByText(/saving removes the\s+programmes you chose/)).toBeVisible();
});

test("an admissions officer sees a postgraduate applicant's qualifications and referees", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await page.getByRole("link", { name: "Admissions" }).click();
  await openRow(page, "Ndinelao Shikongo");
  const record = recordPage(page);
  await expect(record.getByText(/Postgraduate · 2027 Intake/)).toBeVisible();
  await expect(record.getByRole("heading", { name: "Qualifications" })).toBeVisible();
  await expect(record.getByRole("row").filter({ hasText: "68%" }).first()).toBeVisible();
  await expect(record.getByText("Eligible", { exact: true })).toBeVisible();
  await expect(record.getByText("Dr Demo Referee One")).toBeVisible();
  await expect(record.getByText("Degree or Diploma Certificate")).toBeVisible();
  await page.screenshot({ path: "e2e/results/pathway-postgraduate-review.png" });
});

test("a new applicant chooses how they are applying", async ({ page }) => {
  // the start screen, as a signed-in applicant without an application: shown with the demo's open pathways
  await page.route("**/api/method/educore.api.v1.apply.my_application*", (route) =>
    route.fulfill({ json: { message: null } }),
  );
  await signIn(page, "applicant");
  await expect(page.getByRole("heading", { name: "Start your application" })).toBeVisible();
  for (const name of ["Undergraduate", "Mature Age Entry", "Recognition of Prior Learning", "Credit transfer", "Re-admission", "Postgraduate"]) {
    await expect(page.getByRole("radio", { name: new RegExp(`^${name.replace("/", "\\/")}`) })).toBeVisible();
  }
  await expect(page.getByRole("radio", { name: /^Undergraduate/ })).toBeChecked();
  await expect(page.getByText("Are you a citizen or permanent resident of Namibia?")).toBeVisible();
  await page.screenshot({ path: "e2e/results/pathway-start.png", fullPage: true });
});
