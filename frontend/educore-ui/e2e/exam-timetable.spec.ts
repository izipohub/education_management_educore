import { expect, test } from "@playwright/test";
import { signIn } from "./support";

test("the examinations officer sees the session's papers by day and moves one", async ({ page }) => {
  await signIn(page, "examinations-officer.osh");
  await page.getByRole("link", { name: "Examinations", exact: true }).click();
  await page.getByRole("tab", { name: "Timetable" }).click();
  await expect(page.getByText("Semester 2 · ")).toBeVisible();
  const paper = page.getByRole("row").filter({ hasText: "CMP1521" });
  await expect(paper).toContainText("Lecture Room 1");
  await expect(page.getByRole("row").filter({ hasText: /Monday 23-11-2026/ })).toBeVisible();
  await page.screenshot({ path: "e2e/results/exam-timetable.png", fullPage: true });

  await paper.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("CMP1521");
  await expect(dialog.getByRole("button", { name: "Remove" })).toBeVisible();
  await dialog.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText("Paper scheduled")).toBeVisible();

  await page.getByRole("button", { name: "New session" }).click();
  await expect(page.getByRole("dialog")).toContainText("New examination session");
  await page.getByRole("dialog").getByRole("button", { name: "Cancel", exact: true }).click();
});

test("the registrar reads the published timetable", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Examinations", exact: true }).click();
  await page.getByRole("tab", { name: "Timetable" }).click();
  await expect(page.getByText("Published", { exact: true })).toBeVisible();
  await expect(page.getByRole("row").filter({ hasText: "ACC1521" })).toContainText("Lecture Room 1");
  await expect(page.getByRole("button", { name: "New session" })).toHaveCount(0);
});

test("a student sees their papers, and the lecturer their invigilation", async ({ page, browser }) => {
  await signIn(page, "student1.whk");
  await page.getByRole("link", { name: "My studies", exact: true }).click();
  await page.getByRole("tab", { name: "Timetable" }).click();
  const exams = page.locator("section.exams");
  await expect(exams.getByRole("heading", { name: "Examinations" })).toBeVisible();
  await expect(exams.getByRole("row").filter({ hasText: "CMP1521" })).toContainText("Main Hall");
  await expect(exams.getByRole("row").filter({ hasText: "CMP2521" })).toContainText("14:00");

  const other = await browser.newContext();
  const lecturer = await other.newPage();
  await signIn(lecturer, "lecturer.comp.whk");
  await lecturer.getByRole("link", { name: "My modules", exact: true }).click();
  await lecturer.getByRole("tab", { name: "Timetable" }).click();
  await expect(lecturer.getByRole("heading", { name: "Invigilation" })).toBeVisible();
  await expect(lecturer.locator("section.exams").getByRole("row").filter({ hasText: "CMP2521" })).toContainText("Main Hall");
  await other.close();
});
