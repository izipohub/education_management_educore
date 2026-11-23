import { expect, test } from "@playwright/test";
import { signIn, tableRow } from "./support";

test("finance sees student payments and a deposit waiting to be assigned", async ({ page }) => {
  await signIn(page, "student-fees-officer");
  await page.getByRole("link", { name: "Student payments" }).click();
  await expect(page.getByRole("heading", { name: "Student payments" })).toBeVisible();
  await page.getByRole("tab", { name: /^To assign/ }).click();
  const line = tableRow(page, "CASH DEP KEETMANSHOOP BRANCH A BEUKES");
  await expect(line).toBeVisible();
  await line.getByRole("button", { name: "Assign to a student" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Record payment" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/student-payments.png" });
  await dialog.getByRole("button", { name: "Cancel" }).click();
  // not assigned: the demo deposit stays waiting
});

test("a student sees how to pay, with their student number as the reference", async ({ page }) => {
  await signIn(page, "student1.whk");
  await expect(page.getByText("Pay by EFT to")).toBeVisible();
  await expect(page.locator(".reference")).toHaveText(/^EDU-STU-\d{4}-\d{5}$/);
});

test("the registrar has no student payments", async ({ page }) => {
  await signIn(page, "registrar");
  await expect(page.getByRole("link", { name: "Student payments" })).toHaveCount(0);
});
