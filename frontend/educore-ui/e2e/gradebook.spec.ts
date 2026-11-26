import { expect, test } from "@playwright/test";
import { signIn, tableRow } from "./support";

test("a lecturer keeps a gradebook: their assessments, the scores, the CA worked out", async ({ page }) => {
  await signIn(page, "lecturer.accf.kmp");
  await page.getByRole("link", { name: "My modules" }).click();
  await tableRow(page, "FIN2511").getByRole("link").first().click();
  await page.getByRole("tab", { name: "Gradebook" }).click();
  await expect(page.getByText("CA: Test 1 25% · Test 2 25% · Assignment 1 25% · Assignment 2 25%")).toBeVisible();
  const anna = tableRow(page, "Anna Beukes");
  await expect(anna.locator("td.ca")).toHaveText("77.5");
  // the CA follows the scores as they are typed
  const test1 = page.getByRole("spinbutton", { name: "Test 1, Anna Beukes" });
  await test1.fill("50");
  await test1.blur();
  await expect(anna.locator("td.ca")).toHaveText("83.5");
  await page.screenshot({ path: "e2e/results/gradebook.png", fullPage: true });

  // the lecturer's own mix: the shares must add up to 100%
  await page.getByRole("button", { name: "Change assessments" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Total 100%")).toBeVisible();
  await dialog.getByRole("button", { name: "Add an assessment" }).click();
  await dialog.getByRole("spinbutton", { name: "Share 5" }).fill("10");
  await dialog.getByRole("spinbutton", { name: "Share 5" }).blur();
  await expect(dialog.getByText("Total 110% (must be 100%)")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Save assessments" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/gradebook-assessments.png", fullPage: true });
  await dialog.getByRole("button", { name: "Cancel" }).click();
  // not saved: the demo gradebook stays as it is

  await page.getByRole("tab", { name: "Marks" }).click();
  await expect(page.getByText("CA from the gradebook")).toBeVisible();
  await expect(page.getByRole("spinbutton", { name: /^CA, / })).toHaveCount(0);
});
