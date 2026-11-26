import { expect, type Page, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

const nav = (page: Page, name: string) => page.getByRole("navigation", { name: "Main" }).getByRole("link", { name, exact: true });

test("a lecturer reports misconduct from their module, in confidence", async ({ page }) => {
  await signIn(page, "lecturer.accf.kmp");
  await nav(page, "My modules").click();
  await tableRow(page, "FIN2511").getByRole("link").first().click();
  await page.getByRole("button", { name: "Report misconduct" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("To Student Affairs, in confidence");
  await expect(dialog).toContainText("Anna Beukes"); // the module's only student, filled in
  await expect(dialog.getByRole("button", { name: "Report" })).toBeDisabled(); // what happened, first
  await dialog.getByLabel("What happened").fill("Talking during the test");
  await expect(dialog.getByRole("button", { name: "Report" })).toBeEnabled();
  await page.screenshot({ path: "e2e/results/report-misconduct.png", fullPage: true });
  await dialog.getByRole("button", { name: "Cancel" }).click();
  // the lecturer has no Discipline screen: cases are Student Affairs'
  await expect(nav(page, "Discipline")).toHaveCount(0);
});

test("Student Affairs looks into a report and decides a minor case; the campus's only", async ({ page, browser }) => {
  await signIn(page, "student-affairs-officer.kmp");
  await nav(page, "Discipline").click();
  await expect(tableRow(page, "Anna Beukes")).toContainText("Reported");
  await expect(tableRow(page, "Ndapewa Amukoto")).toHaveCount(0); // Windhoek's
  await tableRow(page, "Anna Beukes").getByRole("link").first().click();
  await expect(record(page).getByText("Used a phone during Test 2", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Look into it" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/disciplinary-case.png", fullPage: true });

  const whk = await (await browser.newContext()).newPage();
  await signIn(whk, "student-affairs-officer.whk");
  await nav(whk, "Discipline").click();
  await whk.getByRole("tab", { name: /^Decided/ }).click();
  await tableRow(whk, "Ndapewa Amukoto").getByRole("link").first().click();
  await expect(whk.getByText("Written warning").first()).toBeVisible();
  await expect(whk.getByText(/may appeal until/)).toBeVisible();
});

test("the student sees the decision and may appeal", async ({ page }) => {
  await signIn(page, "student1.whk");
  const card = page.locator("section").filter({ has: page.getByRole("heading", { name: "Disciplinary case" }) }).last();
  await expect(card).toContainText("Written warning");
  await expect(card).toContainText("A first offence, admitted");
  await expect(card).not.toContainText("loud music"); // the report stays with Student Affairs
  await card.getByRole("button", { name: "Appeal" }).click();
  await expect(page.getByRole("dialog").getByRole("button", { name: "Send" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/student-discipline.png", fullPage: true });
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});

test("the Registrar sees every campus and sets the days to appeal", async ({ page }) => {
  await signIn(page, "registrar");
  await nav(page, "Discipline").click();
  await expect(tableRow(page, "Anna Beukes")).toBeVisible();
  await expect(page.getByText(/Appeals within \d+ days/)).toBeVisible();
  await page.getByRole("button", { name: "Change" }).click();
  await expect(page.getByRole("dialog").getByLabel("Days")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});
