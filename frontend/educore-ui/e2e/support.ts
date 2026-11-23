import { expect, type Locator, type Page } from "@playwright/test";

export const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

export async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(login.includes("@") ? login : `${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  // the app changes pages without reloading: there is no "load" event to wait for
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
}

/** A row of a list page (core/ui/DataTable) */
export const tableRow = (page: Page, text: string): Locator => page.getByRole("row").filter({ hasText: text });

/** The record page open (core/ui/RecordPage) */
export const record = (page: Page): Locator => page.getByRole("main");

/** Open a record from its list page and wait for its page */
export async function openRow(page: Page, text: string, heading = text) {
  await tableRow(page, text).getByRole("link", { name: text }).click();
  await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
}

/** A split view's list item (core/ui/SplitView: setup lists) */
export const listItem = (page: Page, text: string): Locator => page.getByRole("option").filter({ hasText: text });

/** The record docked beside the list */
export const pane = (page: Page): Locator => page.getByRole("region", { name: "Details" });

/** Select a record in the list and wait for it to open in the pane */
export async function openRecord(page: Page, text: string, heading = text) {
  await listItem(page, text).click();
  await expect(pane(page).getByRole("heading", { name: heading })).toBeVisible();
}

/** Expand a collapsible section of the open record */
export async function expand(page: Page, section: string) {
  const head = pane(page).getByRole("button", { name: new RegExp(`^${section}`) });
  if ((await head.getAttribute("aria-expanded")) !== "true") await head.click();
}
