import { expect, type Page, test } from "@playwright/test";
import { tableRow } from "./support";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: /^Good (morning|afternoon|evening)/ })).toBeVisible();
}

test("a lecturer sees their modules, and a module's students on its page", async ({ page }) => {
  await signIn(page, "lecturer.accf.kmp");
  await page.getByRole("link", { name: "My modules" }).click();
  // Anna and Petrus are in several of these modules: each is counted once
  await expect(page.getByText("3 modules · 2 students")).toBeVisible();
  await expect(page.getByText("Anna Beukes")).toHaveCount(0); // the class lists are on each module's page
  await page.screenshot({ path: "e2e/results/lecturer-my-modules.png", fullPage: true });
  await tableRow(page, "ACC1511").getByRole("link").first().click();
  await expect(page.getByRole("heading", { level: 1, name: /^ACC1511/ })).toBeVisible();
  await expect(tableRow(page, "Anna Beukes")).toContainText("BACC-KMP-PT · Part-time");
  await expect(tableRow(page, "Petrus Kooper")).toBeVisible();
  await page.getByLabel("Search students").fill("Petrus");
  await expect(tableRow(page, "Anna Beukes")).toHaveCount(0);
});

test("a head of department who lectures sees the colleague on the same course", async ({ page }) => {
  await signIn(page, "hod-lecturer.comp");
  await page.getByRole("link", { name: "My modules" }).click();
  await expect(page.getByText(/with Lecturer COMP Windhoek/).first()).toBeVisible();
});

test("a lecturer without an HR staff record is on record already, with no classes yet", async ({ page }) => {
  await signIn(page, "lecturer");
  await page.getByRole("link", { name: "My modules" }).click();
  await expect(page.getByText(/You are not assigned to any module/)).toBeVisible();
});
