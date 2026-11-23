import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("the head of department sees the department's classes and allocates a lecturer", async ({ page }) => {
  await signIn(page, "hod-lecturer.comp");
  await page.getByRole("link", { name: "Teaching", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Teaching", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Update class lists" })).toBeVisible();
  await page.getByRole("tab", { name: /^Semester 2/ }).click();
  const row = tableRow(page, "Computer Systems").filter({ hasText: "Oshakati" });
  await expect(row).toBeVisible();
  await page.screenshot({ path: "e2e/results/teaching.png", fullPage: true });

  await row.getByRole("link", { name: /Computer Systems/ }).click();
  await expect(record(page).getByRole("heading", { name: "Class list" })).toBeVisible();
  await page.getByRole("combobox", { name: "Add a lecturer" }).click();
  await page.getByRole("option").first().click();
  await expect(page.getByRole("button", { name: "Save", exact: true })).toBeVisible();
  await page.screenshot({ path: "e2e/results/teaching-class.png", fullPage: true });
  await page.getByRole("button", { name: "Undo" }).click();
  // not saved: the demo classes stay as they are
});

test("the registrar reads the allocation only", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Teaching", exact: true }).click();
  await expect(tableRow(page, "Programming Fundamentals").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Update class lists" })).toHaveCount(0);
});
