import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("the bursar sees the waiver Finance requested and can decide on it", async ({ page }) => {
  await signIn(page, "bursar");
  await page.getByRole("link", { name: "Fee waivers", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Fee waivers" })).toBeVisible();
  const row = tableRow(page, "Anna Beukes");
  await expect(row).toContainText("25% of the fees");
  await expect(row).toContainText("Waiting for the Bursar");
  await page.screenshot({ path: "e2e/results/waivers.png", fullPage: true });
  await row.getByRole("button", { name: "Reject" }).click();
  await expect(page.getByRole("dialog").getByRole("button", { name: "Reject" })).toBeDisabled(); // says why first
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});

test("finance requests a waiver from the student's clearance page, and cannot decide its own", async ({ page }) => {
  await signIn(page, "student-fees-officer.kmp");
  await page.getByRole("link", { name: "Fee waivers", exact: true }).click();
  await expect(tableRow(page, "Anna Beukes")).toBeVisible();
  await expect(tableRow(page, "Anna Beukes").getByRole("button", { name: "Approve" })).toHaveCount(0);

  await tableRow(page, "Anna Beukes").getByRole("link", { name: "Anna Beukes" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Anna Beukes" })).toBeVisible();
  await expect(record(page).getByRole("heading", { name: "Fee waivers" })).toBeVisible();
  await page.getByRole("button", { name: "Request a fee waiver" }).click();
  await expect(page.getByRole("dialog").getByRole("button", { name: "Request" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/waiver-request.png", fullPage: true });
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});
