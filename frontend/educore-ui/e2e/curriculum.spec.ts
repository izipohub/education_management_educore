import { expect, test } from "@playwright/test";
import { openRow, record, signIn, tableRow } from "./support";

test("the registrar lays out a programme by year and semester", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Curriculum" }).click();
  await expect(page.getByRole("heading", { name: "Curriculum", exact: true })).toBeVisible();
  await expect(tableRow(page, "Bachelor of Computer Science")).toBeVisible();

  await openRow(page, "Bachelor of Computer Science");
  const year1 = record(page).getByRole("region").or(record(page).locator("section")).filter({ has: page.getByRole("heading", { name: "Year 1" }) });
  await expect(year1.getByText("Semester 1", { exact: true }).first()).toBeVisible();
  await expect(year1.getByText("Programming Fundamentals")).toBeVisible();
  await page.screenshot({ path: "e2e/results/curriculum.png", fullPage: true });

  // moving a course offers to save; undone here, so the demo curriculum stays as it is
  await page.getByRole("combobox", { name: "When Calculus I runs" }).click();
  await page.getByRole("option", { name: "Semester 2" }).click();
  await expect(page.getByText("Unsaved changes")).toBeVisible();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByText("Unsaved changes")).toHaveCount(0);
});

test("lecturers have no curriculum screen", async ({ page }) => {
  await signIn(page, "lecturer.comp.whk");
  await expect(page.getByRole("link", { name: "Curriculum" })).toHaveCount(0);
});
