import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("the registry sees what happened to a student's studies", async ({ page }) => {
  await signIn(page, "registrar");
  await page.getByRole("link", { name: "Students", exact: true }).click();
  await tableRow(page, "Tangeni Iiyambo").getByRole("link", { name: "Tangeni Iiyambo" }).click();
  const history = record(page).locator(".history").filter({ visible: true });
  await expect(history).toContainText("Financial hold placed");
  await expect(history).toContainText("Registered for 2026");
  await expect(history).toContainText("Admitted");
  await page.screenshot({ path: "e2e/results/student-history.png", fullPage: true });
});

test("a student asks to move to another campus", async ({ page }) => {
  await signIn(page, "student1.whk");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Requests", exact: true }).click();
  await page.getByRole("button", { name: "Ask the Registry" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByText("Move campus", { exact: true }).click();
  await expect(dialog).toContainText("Oshakati Campus, full-time");
  await expect(dialog).toContainText("you are at Windhoek Campus now");
  await expect(dialog.getByRole("button", { name: "Send" })).toBeDisabled(); // the reason first
  await page.screenshot({ path: "e2e/results/campus-transfer.png", fullPage: true });
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
});
