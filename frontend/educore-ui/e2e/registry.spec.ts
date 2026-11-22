import { expect, test } from "@playwright/test";
import { listItem, openRecord, pane, signIn } from "./support";

test("a registry officer enrols their campus's admitted applicants", async ({ page }) => {
  await signIn(page, "registry-officer.whk");
  await page.getByRole("link", { name: "Enrolment" }).click();
  await expect(page.getByRole("heading", { name: "Enrolment", exact: true })).toBeVisible();

  await openRecord(page, "Maria Kandjii");
  await expect(pane(page).getByText("N$ 33,400.00")).toBeVisible();
  // the form asks for the login email the applicant never gave (not enrolled: demo data stays as it is)
  await expect(pane(page).getByLabel("Enrolled from")).toHaveValue("01-02-2027");
  const enrolButton = pane(page).getByRole("button", { name: "Enrol", exact: true });
  await expect(enrolButton).toBeDisabled();
  await pane(page).getByLabel("Student's email (their login)").fill("maria.kandjii@example.com");
  await expect(enrolButton).toBeEnabled();
  await page.screenshot({ path: "e2e/results/registry-waiting.png" });
});

test("enrolled students show their fees", async ({ page }) => {
  await signIn(page, "registry-officer.whk");
  await page.getByRole("link", { name: "Enrolment" }).click();
  await page.getByRole("combobox", { name: "Academic year" }).click();
  await page.getByRole("option", { name: "2026", exact: true }).click();
  await page.getByText(/^Enrolled \d/).click();
  await expect(listItem(page, "Ndapewa Amukoto").getByText("Paid")).toBeVisible();
  await openRecord(page, "Lukas Garoeb");
  await expect(pane(page).getByText("N$ 35,500.00 owing")).toBeVisible();
});

test("admissions officers do not enrol", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await expect(page.getByRole("link", { name: "Enrolment" })).toHaveCount(0);
});
