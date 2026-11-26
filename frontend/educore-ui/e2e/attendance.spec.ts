import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("the lecturer opens a module's register and finds who is below the minimum", async ({ page }) => {
  await signIn(page, "lecturer.accf.kmp");
  await page.getByRole("link", { name: "My modules" }).click();
  await tableRow(page, "ACC1511").getByRole("link", { name: "Attendance" }).click();
  await expect(page.getByRole("heading", { level: 1, name: /^ACC1511/ })).toBeVisible();
  await expect(page.getByRole("tab", { name: /^Attendance/ })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("group", { name: "Attendance of Anna Beukes" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mark the rest present" }).or(page.getByRole("button", { name: "Save changes" }))).toBeVisible();
  // a register per lesson: the latest lesson, its time and room
  await expect(page.getByRole("columnheader", { name: /\d\d-\d\d-2026 \d\d:\d\d/ })).toBeVisible();
  await expect(record(page).getByText(/Lecture Room|Computer Laboratory/).first()).toBeVisible();
  // a long class list: only those below the minimum
  await page.getByRole("button", { name: "Below 80% 1" }).click();
  await expect(page.getByRole("group", { name: "Attendance of Petrus Kooper" })).toBeVisible();
  await expect(page.getByRole("group", { name: "Attendance of Anna Beukes" })).toHaveCount(0);
  await expect(record(page).getByText("50%", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /^All / }).click();
  await page.getByLabel("Search students").fill("Anna");
  await expect(page.getByRole("group", { name: "Attendance of Petrus Kooper" })).toHaveCount(0);
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
