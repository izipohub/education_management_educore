import { expect, type Page, test } from "@playwright/test";

const PASSWORD = process.env.EDUCORE_DEMO_PASSWORD ?? "Campus-Demo-2026";

async function signIn(page: Page, login: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`${login}@educore.localhost`);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
}

test("a returning student with fees paid sees the year's courses, ready to register", async ({ page }) => {
  await signIn(page, "student1.whk");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Registration 2027" })).toBeVisible();
  await expect(page.getByText("Year 2 courses")).toBeVisible();
  // the year's required courses are chosen and cannot be dropped
  const structures = page.getByRole("checkbox", { name: /Data Structures and Algorithms/ }).or(page.locator("#c-Data\\ Structures\\ and\\ Algorithms"));
  await expect(structures.first()).toBeChecked();
  await expect(page.getByText("Before you can register")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Submit registration" })).toBeEnabled();
  await page.screenshot({ path: "e2e/results/registration-student.png", fullPage: true });
  // not submitted: the demo student stays free to try it
});

test("a student who owes fees sees what blocks them", async ({ page }) => {
  await signIn(page, "student1.kmp");
  await page.getByRole("link", { name: "Registration", exact: true }).click();
  await expect(page.getByText("Before you can register")).toBeVisible();
  await expect(page.getByText("Outstanding fees: N$ 10,150.00")).toBeVisible();
  await expect(page.getByRole("button", { name: "Submit registration" })).toBeDisabled();
  await page.screenshot({ path: "e2e/results/registration-blocked.png", fullPage: true });
});

test("the faculty officer sees the submitted registrations of their faculty and campus", async ({ page }) => {
  await signIn(page, "faculty-officer.fst.osh");
  await page.getByRole("link", { name: "Registrations" }).click();
  const martha = page.getByRole("row").filter({ hasText: "Martha Shilongo" });
  await expect(martha.getByText("BCS-OSH-FT · year 2")).toBeVisible();
  await martha.getByRole("button", { name: /2 courses, 32 credits/ }).click();
  await expect(martha.getByText("Data Structures and Algorithms")).toBeVisible();
  await expect(martha.getByRole("button", { name: "Approve" })).toBeEnabled();

  // returning asks for a note (cancelled: the demo registration stays waiting)
  await martha.getByRole("button", { name: "Return" }).click();
  await expect(page.getByRole("dialog").getByRole("button", { name: "Return" })).toBeDisabled();
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
  await page.screenshot({ path: "e2e/results/registration-queue.png", fullPage: true });
});
