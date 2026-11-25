import { expect, test } from "@playwright/test";
import { record, signIn } from "./support";

test("the lecturer opens a class register and sees who is below the minimum", async ({ page }) => {
  await signIn(page, "lecturer.accf.kmp");
  await page.getByRole("link", { name: "My teaching" }).click();
  const acc1511 = page.locator("article").filter({ hasText: "ACC1511" });
  await acc1511.getByRole("link", { name: "Attendance" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Attendance: ACC1511" })).toBeVisible();
  await expect(record(page).getByText("Petrus Kooper: 50% attendance, below 80%").filter({ visible: true })).toBeVisible();
  await expect(record(page).getByRole("heading", { name: "Sessions" })).toBeVisible();
  await expect(page.getByRole("group", { name: "Attendance of Anna Beukes" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mark the rest present" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/attendance.png", fullPage: true });
  // not saved: the demo registers stay as they are
});

test("the head of department sees attendance on the class page", async ({ page }) => {
  await signIn(page, "head-of-department.accf");
  await page.goto("/teaching/ACC1511%20KMP%202026");
  await expect(record(page).getByRole("heading", { name: "Attendance" })).toBeVisible();
  await expect(record(page).getByText("8 sessions")).toBeVisible();
});

test("a student sees their class attendance", async ({ page }) => {
  await signIn(page, "student2.kmp");
  await page.getByRole("link", { name: "My studies" }).click();
  await expect(page.getByRole("heading", { name: /Class attendance 2026/ })).toBeVisible();
  await expect(page.getByText("Below the 80% required").first()).toBeVisible();
});
