import { expect, type Page, test } from "@playwright/test";
import { expand, listItem, openRecord, pane } from "./support";

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
  const nangula = listItem(page, "Nangula Haufiku");
  await expect(nangula.getByText("Docs 0/3")).toBeVisible();
  await expect(nangula.getByText("Unpaid")).toBeVisible();

  await openRecord(page, "Nangula Haufiku");
  const record = pane(page);
  // what is outstanding comes first; no offer until it is done
  await expect(record.getByText("3 documents to verify · Application fee outstanding")).toBeVisible();
  await expect(record.getByRole("button", { name: "Make offer" })).toBeDisabled();
  await expect(record.getByRole("link", { name: "Open file" }).first()).toBeVisible();
  await expand(page, "Results");
  await expect(record.getByText("Business Studies")).toBeVisible();
  await page.screenshot({ path: "e2e/results/review-panel.png" });

  // a rejection asks for the reason the applicant will see (cancelled: the demo data stays as it is)
  const birth = record.locator(".doc").filter({ hasText: "Birth Certificate" });
  await birth.getByRole("button", { name: "Reject" }).click();
  await expect(birth.getByRole("button", { name: "Reject" })).toBeDisabled();
  await birth.getByRole("button", { name: "Cancel" }).click();

  await expand(page, "Fee");
  await record.getByRole("button", { name: "Waive the fee" }).click();
  await expect(record.getByRole("button", { name: "Waive", exact: true })).toBeDisabled();
});

test("an applicant sees how to pay, with their application number as the reference", async ({ page }) => {
  await signIn(page, "online.applicant");
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
  await expect(page.getByText("Application fee N$ 150.00")).toBeVisible();
  await expect(page.getByText("Unpaid", { exact: true })).toBeVisible();
  await expect(page.locator(".reference")).toHaveText(/^EDU-APP-\d{4}-\d{5}$/);
  await page.screenshot({ path: "e2e/results/applicant-fee.png", fullPage: true });
});
