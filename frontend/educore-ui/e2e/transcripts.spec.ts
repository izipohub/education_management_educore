import { expect, test } from "@playwright/test";
import { signIn } from "./support";

test("the registry sees transcript requests and what stops issuing them", async ({ page }) => {
  await signIn(page, "registry-officer.kmp");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Transcripts", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: "Anna Beukes" });
  await expect(row).toContainText("Posted to Human Resources, Demo Mining Ltd");
  await expect(row).toContainText("Fees owing");
  await expect(row.getByRole("button", { name: "Issue" })).toBeDisabled();
  await expect(row.getByRole("link", { name: "Print" })).toBeVisible();
  await page.screenshot({ path: "e2e/results/transcripts.png", fullPage: true });
});

test("a student asks for an official transcript", async ({ page }) => {
  await signIn(page, "student1.whk");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Requests", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Official transcripts" })).toBeVisible();
  await page.getByRole("button", { name: "Ask for a transcript" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("The fee is N$");
  await dialog.getByRole("radio", { name: "Email" }).or(dialog.getByRole("button", { name: "Email", exact: true })).first().click();
  await expect(dialog.getByRole("button", { name: "Send" })).toBeDisabled();
  await dialog.getByLabel("Who it is for").fill("Demo Mining Ltd");
  await dialog.getByLabel("Their email address").fill("hr@example.com");
  await expect(dialog.getByRole("button", { name: "Send" })).toBeEnabled();
  await page.screenshot({ path: "e2e/results/transcript-request.png", fullPage: true });
  await dialog.getByRole("button", { name: "Cancel" }).click();
});
