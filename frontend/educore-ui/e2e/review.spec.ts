import { expect, type Page, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(login.includes("@") ? login : `${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  // signed in: the app has moved on from the login page and shows its navigation
  // the app changes pages without reloading, so there is no "load" event to wait for
  await expect(page).not.toHaveURL(/\/login/);
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
}

test("an admissions officer reviews an online application before deciding", async ({ page }) => {
  await signIn(page, "admissions-officer.osh");
  await page.getByRole("link", { name: "Admissions" }).click();
  const nangula = page.getByRole("row").filter({ hasText: "Nangula Haufiku" });
  await expect(nangula.getByText("Documents 0/3")).toBeVisible();
  await expect(nangula.getByText("Fee unpaid")).toBeVisible();
  // not ready: documents unchecked and the fee not received
  await expect(nangula.getByRole("button", { name: "Approve", exact: true })).toBeDisabled();

  await nangula.getByRole("button", { name: "Review" }).click();
  const panel = page.getByRole("dialog");
  await expect(panel.getByText("Incomplete", { exact: true })).toBeVisible();
  // one line: what is outstanding; the full list on request
  await expect(panel.getByText(/3 documents awaiting verification · Application fee outstanding/)).toBeVisible();
  await panel.getByRole("button", { name: "View all", exact: true }).click();
  await expect(panel.getByText("Birth Certificate: verification outstanding")).toBeVisible();
  await panel.getByRole("button", { name: "View all (6)" }).click();
  await expect(panel.getByText("Business Studies")).toBeVisible();
  await expect(panel.getByText(/Open .*\.pdf/).first()).toBeVisible();
  // the panel slides in: wait for it to settle, then it must fit in the window
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));
  const box = await panel.boundingBox();
  const viewport = page.viewportSize();
  expect(box && viewport && box.x >= 0 && box.x + box.width <= viewport.width + 1).toBeTruthy();
  await page.screenshot({ path: "e2e/results/review-panel.png", fullPage: true });

  // a rejection asks for the reason the applicant will see (cancelled: the demo data stays as it is)
  const birth = panel.getByRole("article").filter({ hasText: "Birth Certificate" });
  await birth.getByRole("button", { name: "Reject" }).click();
  await expect(birth.getByRole("button", { name: "Reject" }).last()).toBeDisabled();
  await birth.getByRole("button", { name: "Cancel" }).click();

  await panel.getByRole("button", { name: "Waive the fee" }).click();
  await expect(panel.getByRole("button", { name: "Waive", exact: true })).toBeDisabled();
});

test("an applicant sees how to pay, with their application number as the reference", async ({ page }) => {
  await signIn(page, "online.applicant");
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByText("Application fee N$ 150.00")).toBeVisible();
  await expect(page.getByText("Not received yet")).toBeVisible();
  await expect(page.locator(".reference")).toHaveText(/^EDU-APP-\d{4}-\d{5}$/);
  await page.screenshot({ path: "e2e/results/applicant-fee.png", fullPage: true });
});
