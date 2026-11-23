import { expect, test } from "@playwright/test";
import { openRow, record, signIn, tableRow } from "./support";

test("the registrar reads a programme's curriculum by year and semester", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Curriculum" }).click();
  await expect(page.getByRole("heading", { name: "Curriculum", exact: true })).toBeVisible();
  await openRow(page, "Bachelor of Computer Science");
  await expect(record(page).getByText("Programming Fundamentals")).toBeVisible();
  await expect(record(page).getByText("Semester 1", { exact: true }).first()).toBeVisible();
  // read only: the faculty sets it
  await expect(page.getByText("Set by the faculty")).toBeVisible();
  await expect(page.getByRole("combobox", { name: "When Calculus I runs" })).toHaveCount(0);
});

test("the faculty officer lays out a programme by year and semester", async ({ page }) => {
  await signIn(page, "faculty-officer.fst.osh");
  await page.getByRole("link", { name: "Curriculum" }).click();
  await expect(tableRow(page, "Bachelor of Computer Science")).toBeVisible();
  await openRow(page, "Bachelor of Computer Science");
  await expect(record(page).getByText("Programming Fundamentals")).toBeVisible();
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
