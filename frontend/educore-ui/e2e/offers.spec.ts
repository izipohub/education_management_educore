import { expect, type Page, test } from "@playwright/test";
import { openRow, record, tableRow } from "./support";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
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
  await page.getByRole("tab", { name: /^Offered/ }).click();
  await expect(tableRow(page, "Tomas Iipinge").getByText("Pending", { exact: true })).toBeVisible();
  // paper applications are answered in person
  await expect(tableRow(page, "Maria Kandjii").getByText("Paper")).toBeVisible();

  await openRow(page, "Tomas Iipinge");
  await expect(record(page).getByText("Respond by")).toBeVisible();
  await expect(record(page).getByRole("button", { name: "Extend deadline" })).toBeVisible();
  await expect(record(page).getByText(/^Final NSSCAS results/)).toBeVisible();
});

test("the registry enrols an online applicant only once they accept", async ({ page }) => {
  await signIn(page, "registry-officer.whk");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  await expect(tableRow(page, "Tomas Iipinge").getByText("Pending", { exact: true })).toBeVisible();
  await openRow(page, "Tomas Iipinge");
  await expect(record(page).getByText(/Applicant to accept the offer/).filter({ visible: true })).toBeVisible();
  await expect(record(page).getByRole("button", { name: "Register" })).toHaveCount(0);
  // paper offers are registered as before
  await page.goBack();
  await openRow(page, "Maria Kandjii");
  await expect(record(page).getByRole("button", { name: "Register", exact: true })).toBeVisible();
  await page.screenshot({ path: "e2e/results/offer-registry.png" });
});

test("approving lets admissions offer another of the applicant's choices", async ({ page }) => {
  // shown as ready for a decision (documents and fee are checked by the backend tests); nothing is saved here
  await page.route("**/api/method/educore.api.v1.admissions.review*", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    if (body.message.applicant === "Nangula Haufiku") Object.assign(body.message, { blockers: [], ready: true });
    await route.fulfill({ response, json: body });
  });
  await signIn(page, "admissions-officer.osh");
  await page.getByRole("link", { name: "Admissions" }).click();
  await openRow(page, "Nangula Haufiku");
  await record(page).getByRole("button", { name: "Make offer" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Programme to offer")).toBeVisible();
  await expect(dialog.getByRole("radio", { name: /1\. Bachelor of Accounting/ })).toBeChecked();
  await dialog.getByRole("radio", { name: /2\. Diploma in Information Technology/ }).check();
  await expect(dialog.getByRole("button", { name: "Make offer" })).toBeEnabled();
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running"));
  await page.screenshot({ path: "e2e/results/offer-choice.png" });
  await dialog.getByRole("button", { name: "Cancel" }).click();
});
