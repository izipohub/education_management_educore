import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("the department returns an assessment plan with the reason; the lecturer submits it again", async ({ browser }) => {
  // the Dean: the plan waiting for approval, with its online quiz
  const dean = await (await browser.newContext()).newPage();
  await signIn(dean, "dean.fst");
  await dean.goto("/examinations?tab=plans");
  await expect(tableRow(dean, "CMP2521")).toContainText("Assessment plan to approve");
  await tableRow(dean, "CMP2521").getByRole("link").first().click();
  const plan = record(dean).locator("section").filter({ has: dean.getByRole("heading", { name: "Assessment plan" }) }).last();
  await expect(plan).toContainText("To approve");
  await expect(plan.getByRole("row").filter({ hasText: "Online quiz" })).toContainText("20%");
  await dean.screenshot({ path: "e2e/results/assessment-plan.png", fullPage: true });
  await plan.getByRole("button", { name: "Return to lecturer" }).click();
  await dean.getByLabel("What needs changing").fill("Add a second test before the project");
  await dean.getByRole("dialog").getByRole("button", { name: "Return" }).click();
  await expect(plan).toContainText("Returned: Add a second test before the project");

  // the lecturer: the reason, the faculty's types, then the plan submitted again
  const lecturer = await (await browser.newContext()).newPage();
  await signIn(lecturer, "lecturer.comp.osh");
  await lecturer.getByRole("link", { name: "My modules" }).click();
  await tableRow(lecturer, "CMP2521").getByRole("link").first().click();
  await lecturer.getByRole("tab", { name: "Gradebook" }).click();
  await expect(lecturer.getByText("Add a second test before the project")).toBeVisible();
  // Moodle is not connected on the demo site: the online quiz cannot be linked yet
  await expect(lecturer.getByRole("button", { name: "Link" })).toBeDisabled();
  await lecturer.getByRole("button", { name: "Change assessments" }).click();
  const dialog = lecturer.getByRole("dialog");
  await dialog.getByRole("combobox", { name: "Type 2" }).click();
  await expect(lecturer.getByRole("option", { name: "Online assignment · Moodle" })).toBeVisible();
  await lecturer.keyboard.press("Escape");
  await expect(dialog.getByText("Total 100%")).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await lecturer.screenshot({ path: "e2e/results/gradebook-plan-returned.png", fullPage: true });
  await lecturer.getByRole("button", { name: "Submit for approval" }).click();
  await expect(lecturer.getByText(/With the Head of Department for approval/)).toBeVisible();
  await expect(lecturer.getByRole("spinbutton")).toHaveCount(0); // scores wait for the approval
});

test("the Dean keeps the faculty's assessment types; the head of department reads them", async ({ page }) => {
  await signIn(page, "dean.fst");
  await page.goto("/examinations?tab=rules");
  const types = page.locator("section").filter({ has: page.getByRole("heading", { name: "Assessment types" }) }).last();
  await expect(types.getByLabel("Online quiz online in Moodle")).toBeChecked();
  await types.getByRole("button", { name: "Add a type" }).click();
  await expect(types.getByRole("button", { name: "Save" })).toBeDisabled(); // the new type has no name yet
  await types.getByRole("button", { name: "Undo" }).click();
  await page.screenshot({ path: "e2e/results/assessment-types.png", fullPage: true });

  const hod = await (await page.context().browser()!.newContext()).newPage();
  await signIn(hod, "head-of-department.accf");
  await hod.goto("/examinations?tab=rules");
  const read = hod.locator("section").filter({ has: hod.getByRole("heading", { name: "Assessment types" }) }).last();
  await expect(read).toContainText("Set by the Dean");
  await expect(read.getByRole("row").filter({ hasText: "Online assignment" })).toContainText("Yes");
});

test("a student sees each module's assessments, their due dates and their own scores", async ({ page }) => {
  await signIn(page, "student1.kmp");
  await page.goto("/my-studies?tab=assessments");
  const fin = page.locator("section").filter({ has: page.getByRole("heading", { name: "FIN2511 Corporate Finance" }) }).last();
  await expect(fin).toContainText("CA 77.5 · provisional until the results are published");
  await expect(fin.getByRole("row").filter({ hasText: "Test 1" })).toContainText("14-08-2026");
  await expect(fin.getByRole("row").filter({ hasText: "Test 1" })).toContainText("38 / 50");
  await expect(page.getByText(/No assessments set yet: .*ACC1511/)).toBeVisible();
  await page.screenshot({ path: "e2e/results/student-assessments.png", fullPage: true });
});

test("the Registrar decides when students see their scores", async ({ page }) => {
  await signIn(page, "registrar");
  await page.goto("/examinations?tab=rules");
  await expect(page.getByLabel("Students see their assessment scores as marked")).toBeChecked();
});
