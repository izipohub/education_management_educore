import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

const nav = (page: import("@playwright/test").Page, name: string) => page.getByRole("navigation", { name: "Main" }).getByRole("link", { name, exact: true });

test("a student asks for a service and follows it", async ({ page }) => {
  await signIn(page, "student1.kmp");
  await nav(page, "Requests").click();
  const letter = page.getByRole("link", { name: /Letter of enrolment/ });
  await expect(letter).toContainText("Submitted");
  await expect(letter).toContainText(/Registry · answer by/);
  await page.screenshot({ path: "e2e/results/service-requests-student.png", fullPage: true });

  // a category that needs a document: not sent without one
  await page.getByRole("button", { name: "Ask for a service" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("combobox", { name: "What you need" }).click();
  await page.getByRole("option", { name: "Change of name" }).click();
  await expect(dialog.getByText("Registry answers within 5 working days")).toBeVisible();
  await dialog.getByLabel("Details").fill("Married in October");
  await expect(dialog.getByText("Document (required)")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Send" })).toBeDisabled();
  await dialog.getByRole("button", { name: "Cancel" }).click();

  await letter.click();
  await expect(page.getByRole("heading", { level: 1, name: "Letter of enrolment" })).toBeVisible();
  await expect(record(page).getByText("For the German embassy", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Withdraw" })).toBeVisible();
});

test("the campus's Registry answers; another campus does not see it", async ({ page, browser }) => {
  await signIn(page, "registry-officer.kmp");
  await nav(page, "Service requests").click();
  await expect(tableRow(page, "Anna Beukes")).toContainText("Letter of enrolment");
  await expect(tableRow(page, "Ndapewa Amukoto")).toHaveCount(0); // ICT's, and another campus
  await page.screenshot({ path: "e2e/results/service-requests-office.png", fullPage: true });
  await tableRow(page, "Anna Beukes").getByRole("link").first().click();
  await expect(page.getByRole("button", { name: "Take it" })).toBeVisible();
  await page.getByRole("button", { name: "Decline" }).click();
  await expect(page.getByRole("dialog").getByRole("button", { name: "Decline" })).toBeDisabled(); // the reason first
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
  await page.screenshot({ path: "e2e/results/service-request.png", fullPage: true });

  const osh = await (await browser.newContext()).newPage();
  await signIn(osh, "registry-officer.osh");
  await nav(osh, "Service requests").click();
  await expect(tableRow(osh, "Anna Beukes")).toHaveCount(0);
});

test("ICT sees the conversation on its request", async ({ page }) => {
  await signIn(page, "ict-administrator");
  await nav(page, "Service requests").click();
  await tableRow(page, "Ndapewa Amukoto").getByRole("link").first().click();
  await expect(page.getByText("It says my password is wrong.")).toBeVisible();
  await expect(page.getByText("Ndapewa Amukoto").first()).toBeVisible();
});

test("the Registrar keeps the categories", async ({ page }) => {
  await signIn(page, "registrar");
  await nav(page, "Service request categories").click();
  await expect(tableRow(page, "Change of name")).toContainText("Document required");
  await page.getByRole("button", { name: "Letter of enrolment" }).click();
  await expect(page.getByLabel("Working days to respond")).toHaveValue("2");
  await page.screenshot({ path: "e2e/results/service-categories.png", fullPage: true });
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});
