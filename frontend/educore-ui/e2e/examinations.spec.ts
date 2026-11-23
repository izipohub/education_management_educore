import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("a lecturer enters a class's marks and sees the results worked out", async ({ page }) => {
  await signIn(page, "lecturer.comp.whk");
  await page.getByRole("link", { name: "My teaching" }).click();
  const databases = page.getByRole("article").filter({ hasText: "CMP2521" });
  await databases.getByRole("link", { name: "Marks" }).click();
  await expect(page.getByRole("heading", { name: /^Marks: CMP2521/ })).toBeVisible();
  const ca = page.getByRole("spinbutton", { name: /^CA, / }).first();
  await ca.fill("70");
  await page.getByRole("spinbutton", { name: /^Examination, / }).first().fill("60");
  await page.getByRole("spinbutton", { name: /^Examination, / }).first().blur();
  // CA 50%, examination 50%: 65, a B and a pass
  await expect(page.locator("td.final").first()).toHaveText("65");
  await expect(record(page).getByText("Pass", { exact: true }).first()).toBeVisible();
  await page.screenshot({ path: "e2e/results/marks-entry.png", fullPage: true });
  // not saved: the demo marks stay as they are
});

test("the head of department sees marks to moderate", async ({ page }) => {
  await signIn(page, "hod-lecturer.comp");
  await page.getByRole("link", { name: "Examinations" }).click();
  await page.getByRole("tab", { name: /^To moderate/ }).click();
  const row = tableRow(page, "Computer Systems");
  await expect(row).toBeVisible();
  await row.getByRole("link", { name: /Computer Systems/ }).click();
  await expect(page.getByRole("button", { name: "Moderated" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Return to lecturer" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/marks-moderation.png", fullPage: true });
});

test("the registrar reads the results and sets the rules", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Examinations" }).click();
  await page.getByRole("tab", { name: /^Published/ }).click();
  await expect(tableRow(page, "Programming Fundamentals").first()).toBeVisible();
  await page.getByRole("tab", { name: "Rules" }).click();
  await expect(page.getByLabel("Pass mark")).toBeEnabled();
  await page.screenshot({ path: "e2e/results/exam-rules.png", fullPage: true });
});

test("a student sees their published results", async ({ page }) => {
  await signIn(page, "student1.osh");
  await expect(page.getByRole("heading", { name: "Results 2026" })).toBeVisible();
});
