import { expect, test } from "@playwright/test";
import { signIn } from "./support";

test("ICT sees the Moodle connection, off until an address and token are given", async ({ page }) => {
  await signIn(page, "ict-administrator");
  await page.getByRole("link", { name: "Integrations" }).click();
  await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible();
  await expect(page.getByText("Not connected")).toBeVisible();
  await expect(page.getByRole("button", { name: "Test connection" })).toBeDisabled();
  await page.getByLabel("Moodle address").fill("https://moodle.example.edu.na");
  await expect(page.getByRole("button", { name: "Test connection" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Save", exact: true })).toBeVisible();
  await page.screenshot({ path: "e2e/results/integrations.png", fullPage: true });
  // not saved: the demo site stays without Moodle
});

test("the registrar has no integrations", async ({ page }) => {
  await signIn(page, "registrar");
  await expect(page.getByRole("link", { name: "Integrations" })).toHaveCount(0);
});
