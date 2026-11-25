import { expect, test } from "@playwright/test";
import { openRow, record, signIn, tableRow } from "./support";

const NSFAF = "Namibia Students Financial Assistance Fund";

test("financial aid sees what each sponsor was invoiced and owes, and the students it pays for", async ({ page }) => {
  await signIn(page, "financial-aid-officer");
  await page.getByRole("link", { name: "Sponsors", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sponsors", exact: true })).toBeVisible();
  await expect(tableRow(page, NSFAF)).toContainText("N$ 16,500.00");
  await page.screenshot({ path: "e2e/results/sponsors.png", fullPage: true });

  await openRow(page, NSFAF);
  const student = record(page).getByRole("row").filter({ hasText: "Martha Shilongo" });
  await expect(student).toContainText("Full fees");
  await expect(student).toContainText("NSFAF-2026-11873");
  await expect(student).toContainText("Invoiced");
  await expect(record(page).getByText("NSFAF TUITION PAYMENT").or(record(page).getByText("N$ 15,000.00")).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Statement 2026/ })).toBeVisible();
  await page.screenshot({ path: "e2e/results/sponsor.png", fullPage: true });

  await page.getByRole("button", { name: "Add student" }).click();
  await expect(page.getByRole("dialog")).toContainText("Add a student for 2026");
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});

test("a new sponsor starts from a blank form", async ({ page }) => {
  await signIn(page, "bursar");
  await page.getByRole("link", { name: "Sponsors", exact: true }).click();
  await page.getByRole("button", { name: "New sponsor" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "New sponsor" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add sponsor" })).toBeDisabled();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("heading", { name: "Sponsors", exact: true })).toBeVisible();
});

test("the student record says who pays the fees", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Students", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Students", exact: true })).toBeVisible();
  await openRow(page, "Martha Shilongo");
  await expect(record(page).getByText(`${NSFAF} · Full fees`)).toBeVisible();
});

test("the registry does not see sponsors", async ({ page }) => {
  await signIn(page, "registry-officer");
  await expect(page.getByRole("link", { name: "Sponsors", exact: true })).toHaveCount(0);
});
