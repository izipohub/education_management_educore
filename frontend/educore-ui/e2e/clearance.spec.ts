import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("finance sees students on hold and what stops their clearance", async ({ page }) => {
  await signIn(page, "student-fees-officer.osh");
  await page.getByRole("link", { name: "Clearance", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Financial clearance" })).toBeVisible();
  await expect(tableRow(page, "Tangeni Iiyambo")).toBeVisible();
  await expect(tableRow(page, "Petrus Kooper")).toHaveCount(0); // another campus
  await page.screenshot({ path: "e2e/results/clearance.png", fullPage: true });

  await tableRow(page, "Tangeni Iiyambo").getByRole("link", { name: "Tangeni Iiyambo" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Tangeni Iiyambo" })).toBeVisible();
  await expect(record(page).getByText("Hold: Payment arrangement for the 2026 fees not kept").filter({ visible: true })).toBeVisible();
  await expect(record(page).getByRole("button", { name: "Lift", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Place a hold" }).click();
  await expect(page.getByRole("button", { name: "Place hold" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/clearance-student.png", fullPage: true });
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});

test("the registry sees the hold on the student record, and the student on My studies", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Students", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Students", exact: true })).toBeVisible();
  await tableRow(page, "Tangeni Iiyambo").getByRole("link", { name: "Tangeni Iiyambo" }).click();
  await expect(record(page).getByRole("heading", { name: "Financial hold" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Clearance", exact: true })).toHaveCount(0);
});

test("a student on hold is told why", async ({ page }) => {
  await signIn(page, "student2.osh");
  await page.getByRole("link", { name: "My studies" }).click();
  await expect(page.getByText("Financial hold: Payment arrangement for the 2026 fees not kept. Contact Finance.")).toBeVisible();
});
