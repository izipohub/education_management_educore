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
  await expect(page.getByText("ACC1511").first()).toBeVisible();
  await expect(page.getByText("N$ 10,150.00 overdue")).toBeVisible();
  await page.screenshot({ path: "e2e/results/student-my-studies.png", fullPage: true });
  // the statement, on Fees: from the fees charged, through the payment, to what is owed
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Fees", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: "Payment EFT-DEMO" })).toContainText("N$ 10,150.00");
});

test("a student who has paid sees that they are paid up", async ({ page }) => {
  await signIn(page, "student1.whk");
  await expect(page.getByRole("heading", { name: "Ndapewa Amukoto" })).toBeVisible();
  await expect(page.getByText("Paid up")).toBeVisible();
});

test("staff have no student page", async ({ page }) => {
  await signIn(page, "registrar");
  await expect(page.getByRole("heading", { name: /^Good (morning|afternoon|evening)/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "My studies" })).toHaveCount(0);
  await page.goto("/my-studies");
  await expect(page.getByRole("heading", { name: /^Good (morning|afternoon|evening)/ })).toBeVisible();
});

test("a student asks the Registry to interrupt their studies", async ({ page }) => {
  await signIn(page, "student1.whk");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Requests", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Interrupting, cancelling or moving campus" })).toBeVisible();
  await page.getByRole("button", { name: "Ask the Registry" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Send" })).toBeDisabled();
  await dialog.getByLabel("Reason").fill("Family responsibilities");
  await expect(dialog.getByRole("button", { name: "Send" })).toBeEnabled();
  await dialog.getByRole("group", { name: "Request" }).getByRole("button", { name: "Cancel studies" }).click();
  await expect(dialog.getByLabel("Returning in")).toHaveCount(0);
  await page.screenshot({ path: "e2e/results/studies-request.png", fullPage: true });
  // not sent: the demo student stays as she is
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
});
