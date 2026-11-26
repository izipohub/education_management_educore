import { expect, test } from "@playwright/test";
import { signIn } from "./support";

test("the timetable officer sees the campus's week, the classes and the rooms", async ({ page }) => {
  await signIn(page, "timetable-officer.whk");
  await page.getByRole("link", { name: "Timetable", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Timetable", exact: true })).toBeVisible();
  const times = page.locator(".week button.slot");
  await expect(times.first()).toBeVisible();
  await expect(page.getByText("All placed")).toBeVisible();
  await page.screenshot({ path: "e2e/results/timetable.png", fullPage: true });

  await times.first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Class time");
  await expect(dialog.getByRole("button", { name: "Remove" })).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();

  await page.getByRole("tab", { name: /^Rooms/ }).click();
  await expect(page.getByRole("row").filter({ hasText: "Computer Laboratory 1" })).toContainText("Computer laboratory");
  await expect(page.getByRole("button", { name: "Add a room" })).toBeVisible();
});

test("the registrar reads the timetable only", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Timetable", exact: true }).click();
  await expect(page.locator(".week .slot").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Add a class time" })).toHaveCount(0);
  await expect(page.locator(".week button.slot")).toHaveCount(0);
});

test("a student sees their week on My studies", async ({ page }) => {
  await signIn(page, "student1.whk");
  await page.getByRole("link", { name: "My studies", exact: true }).click();
  await page.getByRole("tab", { name: "Timetable" }).click();
  await expect(page.getByRole("heading", { name: /^Semester \d \d{4}/ })).toBeVisible();
  await expect(page.locator(".week .slot").first()).toBeVisible();
  await page.screenshot({ path: "e2e/results/student-timetable.png", fullPage: true });
});

test("a lecturer sees their week on My modules", async ({ page }) => {
  await signIn(page, "lecturer.comp.whk");
  await page.getByRole("link", { name: "My modules", exact: true }).click();
  await page.getByRole("tab", { name: "Timetable" }).click();
  await expect(page.locator(".week .slot").filter({ hasText: "Lecture Room 1" }).first()).toBeVisible();
  await page.screenshot({ path: "e2e/results/lecturer-timetable.png", fullPage: true });
});
