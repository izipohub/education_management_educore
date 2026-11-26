import { expect, test } from "@playwright/test";
import { signIn } from "./support";

test("the registrar's dashboard leads to the work waiting", async ({ page }) => {
  await signIn(page, "registrar");
  await expect(page.getByRole("heading", { name: /^Good (morning|afternoon|evening), Registrar/ })).toBeVisible();
  const decide = page.locator(".stat").filter({ hasText: "To decide" });
  await expect(decide.getByText(/^\d+$/)).toBeVisible();
  // the full offering is named in words, not by colour
  await expect(page.getByRole("row").filter({ hasText: "BSAMS-WHK-FT" }).getByText("Full")).toBeVisible();
  // the oldest applications waiting open their own page; the year in charts
  await expect(page.getByRole("heading", { name: "Awaiting a decision" })).toBeVisible();
  await expect(page.getByRole("img", { name: /^Applications received per month/ })).toBeVisible();
  await expect(page.getByRole("group", { name: "Applications by channel" }).getByText("Paper", { exact: true })).toBeVisible();

  // one campus at a time
  await page.getByRole("combobox", { name: "Campus" }).click();
  await page.getByRole("option", { name: "Oshakati Campus" }).click();
  await expect(page).toHaveURL(/campus=Oshakati/);
  await expect(page.getByText(/^Oshakati Campus · /)).toBeVisible();
  await page.screenshot({ path: "e2e/results/dashboard-registrar.png", fullPage: true });

  await decide.getByRole("link", { name: /Review/ }).click();
  await expect(page.getByRole("heading", { name: "Admissions", exact: true })).toBeVisible();
});

test("the bursar sees student fees collected per campus", async ({ page }) => {
  await signIn(page, "bursar");
  await expect(page.getByRole("heading", { name: /Student fees \d{4}/ })).toBeVisible();
  await expect(page.getByRole("list", { name: "Fees collected against invoiced, per campus" }).getByRole("listitem")).toHaveCount(3);
  // nothing of admissions for finance
  await expect(page.getByText("To decide", { exact: true })).toHaveCount(0);
});

test("each person's home shows what is waiting for them, and opens it", async ({ page }) => {
  await signIn(page, "dean.fst");
  const waiting = page.locator("section").filter({ has: page.getByRole("heading", { name: "Waiting for you" }) }).last();
  await expect(waiting.getByRole("link", { name: /Assessment plans to approve/ })).toBeVisible();
  await page.screenshot({ path: "e2e/results/home-dean.png", fullPage: true });
  await waiting.getByRole("link", { name: /Assessment plans to approve/ }).click();
  await expect(page.getByRole("heading", { name: "Approvals", exact: true })).toBeVisible();
});

test("a lecturer's home shows today's lessons and their registers", async ({ page }) => {
  await signIn(page, "lecturer.comp.whk");
  await expect(page.getByRole("heading", { name: "Today", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Waiting for you" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/home-lecturer.png", fullPage: true });
});

test("a student's studies open on what is coming up", async ({ page }) => {
  await signIn(page, "student1.kmp");
  await expect(page.getByRole("heading", { name: "Coming up" })).toBeVisible();
});
