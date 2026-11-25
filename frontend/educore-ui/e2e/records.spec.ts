import { expect, test } from "@playwright/test";
import { openRow, record, signIn, tableRow } from "./support";

test("the registrar finds a student and sees their record", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Students", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Students", exact: true })).toBeVisible();
  await expect(tableRow(page, "Martha Shilongo")).toBeVisible();

  await openRow(page, "Martha Shilongo");
  // the particulars from the application, and the next of kin as a guardian
  await expect(record(page).getByText("05112500198")).toBeVisible();
  await expect(record(page).getByText(/Ndeshi Shilongo/)).toBeVisible();
  await expect(record(page).getByText("NSFAF")).toBeVisible();
  await expect(record(page).getByRole("heading", { name: "Registration" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/student-record.png", fullPage: true });

  // the proof of registration is a PDF
  const href = await record(page).getByRole("link", { name: /^Proof of registration/ }).getAttribute("href");
  const pdf = await page.request.get(href!);
  expect(pdf.headers()["content-type"]).toContain("application/pdf");
});

test("a registry officer sees their campus's students only", async ({ page }) => {
  await signIn(page, "registry-officer.osh");
  await page.getByRole("link", { name: "Students", exact: true }).click();
  await expect(tableRow(page, "Martha Shilongo")).toBeVisible();
  await expect(tableRow(page, "Ndapewa Amukoto")).toHaveCount(0);
});

test("finance sees application fees and waives one with a reason", async ({ page }) => {
  await signIn(page, "finance-officer");
  await page.getByRole("link", { name: "Application fees" }).click();
  await expect(page.getByRole("heading", { name: "Application fees" })).toBeVisible();
  const nangula = tableRow(page, "Nangula Haufiku");
  await expect(nangula).toBeVisible();
  await nangula.getByRole("button", { name: "Waive" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: /^Waive N\$/ })).toBeDisabled();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  // not waived: the demo fee stays outstanding
});

test("admissions downloads the offer letter as a PDF", async ({ page }) => {
  await signIn(page, "admissions-officer.whk");
  await page.getByRole("link", { name: "Admissions" }).click();
  await page.getByRole("tab", { name: /^Offered/ }).click();
  await openRow(page, "Tomas Iipinge");
  const href = await record(page).getByRole("link", { name: "Offer letter (PDF)" }).getAttribute("href");
  const pdf = await page.request.get(href!);
  expect(pdf.headers()["content-type"]).toContain("application/pdf");
});

test("the registry decides requests to interrupt or cancel studies; the faculty does not", async ({ page }) => {
  await signIn(page, "registry-officer.osh");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Students" }).click();
  await page.getByRole("tab", { name: /^Requests/ }).click();
  await expect(page.getByText("No requests here")).toBeVisible();

  await page.context().clearCookies();
  await signIn(page, "faculty-officer.fst.osh");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Students" }).click();
  await expect(page.getByRole("tab", { name: /^Requests/ })).toHaveCount(0);
});
