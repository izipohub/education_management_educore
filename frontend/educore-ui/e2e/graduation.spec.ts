import { expect, test } from "@playwright/test";
import { signIn, tableRow } from "./support";

test("the registrar sees each student's progress towards completing their programme", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Graduation" }).click();
  await expect(page.getByRole("heading", { name: "Graduation" })).toBeVisible();
  // the demo students are in their first year: credits passed against the programme's total, courses still to pass
  const row = tableRow(page, "EDU-STU-2026-00005");
  await expect(row).toContainText("64 of 360");
  await expect(row).toContainText("Corporate Finance");
  await expect(row).toContainText("Not yet");
  await page.screenshot({ path: "e2e/results/graduation.png", fullPage: true });
  await page.getByRole("tab", { name: /^Completed/ }).click();
  await expect(page.getByText("No students here")).toBeVisible();
});

test("the examinations office reads the list; students have no graduation screen", async ({ page }) => {
  await signIn(page, "examinations-officer.osh");
  await page.getByRole("link", { name: "Graduation" }).click();
  await expect(tableRow(page, "EDU-STU-2026-00004")).toContainText("On hold");
  await expect(page.getByRole("button", { name: /^Record/ })).toHaveCount(0);

  await page.context().clearCookies();
  await signIn(page, "student1.osh");
  await expect(page.getByRole("link", { name: "Graduation" })).toHaveCount(0);
});
