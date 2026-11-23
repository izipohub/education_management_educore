import { expect, type Page, test } from "@playwright/test";
import { openRow, record, tableRow } from "./support";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(login.includes("@") ? login : `${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  // signed in: the app has moved on from the login page and shows its navigation
  // the app changes pages without reloading, so there is no "load" event to wait for
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
}

test("an admissions officer reviews an online application before deciding", async ({ page }) => {
  await signIn(page, "admissions-officer.osh");
  await page.getByRole("link", { name: "Admissions" }).click();
  const nangula = tableRow(page, "Nangula Haufiku");
  await expect(nangula.getByText("0 of 3 verified")).toBeVisible();
  await expect(nangula.getByText("Unpaid")).toBeVisible();

  await openRow(page, "Nangula Haufiku");
  const page_ = record(page);
  // what is outstanding is listed in words; the offer waits until it is done, and its button says why
  await expect(page_.getByRole("heading", { name: "Outstanding" })).toBeVisible();
  await expect(page_.getByText("0 of 3 verified")).toBeVisible();
  const offer = page_.getByRole("button", { name: "Make offer" });
  await expect(offer).toBeDisabled();
  await expect(offer).toHaveAttribute("title", "3 documents to verify · Application fee outstanding");
  await expect(page_.getByRole("link", { name: "Birth Certificate" })).toBeVisible();
  await expect(page_.getByText("Business Studies")).toBeVisible();
  await page.screenshot({ path: "e2e/results/review-panel.png", fullPage: true });

  // a rejection asks for the reason the applicant will see (cancelled: the demo data stays as it is)
  await tableRow(page, "Birth Certificate").getByRole("button", { name: "Reject" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Reject", exact: true })).toBeDisabled();
  await dialog.getByRole("button", { name: "Cancel" }).click();

  // waiving the fee is Finance's decision, not admissions'
  await expect(page_.getByRole("button", { name: "Waive the fee" })).toHaveCount(0);
});

test("an applicant sees how to pay, with their application number as the reference", async ({ page }) => {
  await signIn(page, "online.applicant");
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByText("Application fee N$ 150.00")).toBeVisible();
  await expect(page.getByText("Unpaid", { exact: true })).toBeVisible();
  await expect(page.locator(".reference")).toHaveText(/^EDU-APP-\d{4}-\d{5}$/);
  await page.screenshot({ path: "e2e/results/applicant-fee.png", fullPage: true });
});
