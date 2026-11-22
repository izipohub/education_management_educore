import { expect, type Page, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

test("an applicant sees their offer, its conditions and deadline, and the letter", async ({ page }) => {
  await signIn(page, "offer.applicant");
  await expect(page.getByText("Offered", { exact: true })).toBeVisible();
  const offer = page.getByRole("article").filter({ has: page.getByRole("heading", { name: "Offer of a place" }) });
  await expect(offer.getByText("Bachelor of Computer Science", { exact: true })).toBeVisible();
  await expect(offer.getByText(/Conditions: Final NSSCAS results/)).toBeVisible();
  await expect(offer.getByText(/Please respond by/)).toBeVisible();

  // the letter on request
  await expect(page.getByLabel("Offer letter", { exact: true })).toHaveCount(0);
  await offer.getByRole("button", { name: "View offer letter" }).click();
  await expect(page.getByLabel("Offer letter", { exact: true }).getByText(/We are pleased to offer you a place/)).toBeVisible();
  await page.screenshot({ path: "e2e/results/offer-applicant.png", fullPage: true });

  // declining asks for confirmation (cancelled: the demo offer stays open)
  await offer.getByRole("button", { name: "Decline" }).click();
  await expect(offer.getByText(/Declining cannot be undone/)).toBeVisible();
  await offer.getByRole("button", { name: "Cancel" }).click();
  await expect(offer.getByRole("button", { name: "Accept offer" })).toBeEnabled();
});

test("admissions sees the offer awaiting a response", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await page.getByRole("link", { name: "Admissions" }).click();
  await page.getByRole("radio", { name: /^Approved/ }).or(page.getByRole("button", { name: /^Approved/ })).first().click();
  const tomas = page.getByRole("row").filter({ hasText: "Tomas Iipinge" });
  await expect(tomas.getByText("Pending", { exact: true })).toBeVisible();
  await expect(tomas.getByText(/^by /)).toBeVisible();
  // paper applications are answered in person
  await expect(page.getByRole("row").filter({ hasText: "Maria Kandjii" }).getByText("In person")).toBeVisible();

  await tomas.getByRole("button", { name: "Review" }).click();
  const panel = page.getByRole("dialog");
  await expect(panel.getByRole("button", { name: "Extend deadline" })).toBeVisible();
  await expect(panel.getByText(/Conditions: Final NSSCAS results/)).toBeVisible();
});

test("the registry enrols an online applicant only once they accept", async ({ page }) => {
  await signIn(page, "registry-officer.whk");
  await page.getByRole("link", { name: "Enrolment" }).click();
  const tomas = page.getByRole("row").filter({ hasText: "Tomas Iipinge" });
  await expect(tomas.getByText("Pending", { exact: true })).toBeVisible();
  await expect(tomas.getByRole("button", { name: "Enrol" })).toHaveCount(0);
  // paper offers are enrolled as before
  await expect(page.getByRole("row").filter({ hasText: "Maria Kandjii" }).getByRole("button", { name: "Enrol" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/offer-registry.png", fullPage: true });
});
