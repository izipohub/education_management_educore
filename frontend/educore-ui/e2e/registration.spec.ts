import { expect, type Page, test } from "@playwright/test";
import { openRow, record, tableRow } from "./support";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
}

test("a returning student with fees paid sees the year's courses, ready to register", async ({ page }) => {
  await signIn(page, "student1.whk");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Registration 2027" })).toBeVisible();
  await expect(page.getByText("Year 2 courses")).toBeVisible();
  // the year's required courses are chosen and cannot be dropped
  const structures = page.getByRole("checkbox", { name: /Data Structures and Algorithms/ }).or(page.locator("#c-Data\\ Structures\\ and\\ Algorithms"));
  await expect(structures.first()).toBeChecked();
  await expect(page.getByText("Before you can register")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Submit registration" })).toBeEnabled();
  await page.screenshot({ path: "e2e/results/registration-student.png", fullPage: true });
  // not submitted: the demo student stays free to try it
});

test("a student who owes fees sees what blocks them", async ({ page }) => {
  await signIn(page, "student1.kmp");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  await expect(page.getByText("Before you can register")).toBeVisible();
  await expect(page.getByText("Outstanding fees: N$ 10,150.00")).toBeVisible();
  await expect(page.getByRole("button", { name: "Submit registration" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/registration-blocked.png", fullPage: true });
});

test("the faculty officer sees the submitted registrations of their faculty and campus", async ({ page }) => {
  await signIn(page, "faculty-officer.fst.osh");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  // a faculty officer has senior students only: no choice of group
  await expect(page.getByRole("group", { name: "Students" })).toHaveCount(0);
  await expect(tableRow(page, "Martha Shilongo").getByText("32")).toBeVisible();
  await openRow(page, "Martha Shilongo");
  await expect(record(page).getByText("Data Structures and Algorithms")).toBeVisible();
  await expect(record(page).getByRole("button", { name: "Approve" })).toBeEnabled();

  // returning asks for a note (cancelled: the demo registration stays waiting)
  await record(page).getByRole("button", { name: "Return" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Return to student" })).toBeDisabled();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await page.screenshot({ path: "e2e/results/registration-queue.png" });
});

test("the registrar has first-year and senior students under one Registration item", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  const groups = page.getByRole("group", { name: "Students" });
  await expect(groups.getByRole("button", { name: "First-year students" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("tab", { name: /^To register/ })).toBeVisible();

  await groups.getByRole("button", { name: "Senior students" }).click();
  await expect(page).toHaveURL(/group=senior/);
  await expect(page.getByRole("row").filter({ hasText: "Martha Shilongo" })).toBeVisible();
  // a record's back link returns to the same group
  await page.getByRole("link", { name: "Martha Shilongo" }).click();
  await page.getByRole("link", { name: /^Registration · senior students/ }).click();
  await expect(groups.getByRole("button", { name: "Senior students" })).toHaveAttribute("aria-pressed", "true");
});
