import { expect, type Page, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("a student lands on their own studies: programme, courses and fees", async ({ page }) => {
  await signIn(page, "student1.kmp");
  await expect(page).toHaveURL(/\/my-studies$/);
  await expect(page.getByRole("heading", { name: "Anna Beukes" })).toBeVisible();
  await expect(page.getByText("Bachelor of Accounting", { exact: true })).toBeVisible();
  await expect(page.getByText("NQF level 7")).toBeVisible();
  await expect(page.getByText("ACC1511")).toBeVisible();
  await expect(page.getByText("N$ 10,150.00 overdue")).toBeVisible();
  // the statement runs from the fees charged, through the payment, to what is owed
  await expect(page.getByRole("row").filter({ hasText: "Payment EFT-DEMO" })).toContainText("N$ 10,150.00");
  await page.screenshot({ path: "e2e/results/student-my-studies.png", fullPage: true });
});

test("a student who has paid sees that they are paid up", async ({ page }) => {
  await signIn(page, "student1.whk");
  await expect(page.getByRole("heading", { name: "Ndapewa Amukoto" })).toBeVisible();
  await expect(page.getByText("Paid up")).toBeVisible();
});

test("staff have no student page", async ({ page }) => {
  await signIn(page, "registrar");
  await expect(page.getByRole("heading", { name: /Welcome/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "My studies" })).toHaveCount(0);
  await page.goto("/my-studies");
  await expect(page.getByRole("heading", { name: /Welcome/ })).toBeVisible();
});
