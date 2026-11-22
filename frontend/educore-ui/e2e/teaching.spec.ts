import { expect, type Page, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: /^Good (morning|afternoon|evening)/ })).toBeVisible();
}

test("a lecturer sees their classes and the students in them", async ({ page }) => {
  await signIn(page, "lecturer.accf.kmp");
  await page.getByRole("link", { name: "My teaching" }).click();
  // Anna and Petrus are in several of these classes: each is counted once
  await expect(page.getByText("3 classes · 2 students")).toBeVisible();
  const acc1511 = page.getByRole("article").filter({ hasText: "ACC1511" });
  await expect(acc1511.getByText("Anna Beukes")).toBeVisible();
  await expect(acc1511.getByText("Petrus Kooper")).toBeVisible();
  await expect(acc1511.getByText("BACC-KMP-PT · Part-time")).toBeVisible();
  await page.screenshot({ path: "e2e/results/lecturer-my-teaching.png", fullPage: true });
});

test("a head of department who lectures sees the colleague on the same course", async ({ page }) => {
  await signIn(page, "hod-lecturer.comp");
  await page.getByRole("link", { name: "My teaching" }).click();
  await expect(page.getByText("With Lecturer COMP Windhoek").first()).toBeVisible();
});

test("a lecturer login not yet linked to HR is told what to do", async ({ page }) => {
  await signIn(page, "lecturer");
  await page.getByRole("link", { name: "My teaching" }).click();
  await expect(page.getByText(/not yet linked to your staff record/)).toBeVisible();
});
