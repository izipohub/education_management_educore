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

  // the plan was approved by the Head of Department: it is changed only once the department returns it
  await expect(page.getByText("Approved", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Change assessments" })).toHaveCount(0);

  await page.getByRole("tab", { name: "Marks" }).click();
  await expect(page.getByText("CA from the gradebook")).toBeVisible();
  await expect(page.getByRole("spinbutton", { name: /^CA, / })).toHaveCount(0);
});
