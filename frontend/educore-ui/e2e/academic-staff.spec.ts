import { expect, test } from "@playwright/test";
import { record, signIn, tableRow } from "./support";

test("the head of department sees the department's lecturers and what their setup needs", async ({ page }) => {
  await signIn(page, "head-of-department.accf");
  await page.getByRole("link", { name: "Academic staff", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Academic staff", exact: true })).toBeVisible();
  await expect(tableRow(page, "Lecturer ACCF Keetmanshoop")).toContainText("Ready");
  await expect(tableRow(page, "Lecturer COMP Windhoek")).toHaveCount(0); // another faculty
  await page.getByRole("tab", { name: /^Incomplete/ }).click();
  await expect(tableRow(page, "Lecturer ACCF Windhoek and Oshakati")).toContainText("HR staff record missing");
  await page.screenshot({ path: "e2e/results/academic-staff.png", fullPage: true });

  await tableRow(page, "Lecturer ACCF Windhoek and Oshakati").getByRole("link", { name: "Lecturer ACCF Windhoek and Oshakati" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Lecturer ACCF Windhoek and Oshakati" })).toBeVisible();
  await expect(record(page).getByText("HR staff record to be linked by HR").filter({ visible: true })).toBeVisible();
  await expect(record(page).getByText("Windhoek Campus, Oshakati Campus")).toBeVisible();
  await expect(page.getByRole("button", { name: "Link staff record" })).toHaveCount(0); // HR's
  await page.getByRole("button", { name: "Edit" }).click();
  await expect(page.getByLabel("Department")).toBeVisible();
  await page.screenshot({ path: "e2e/results/lecturer.png", fullPage: true });
  await page.getByRole("button", { name: "Cancel" }).click();
});

test("HR links staff records; the lecturer's classes are listed", async ({ page }) => {
  await signIn(page, "hr-manager");
  await page.getByRole("link", { name: "Academic staff", exact: true }).click();
  await tableRow(page, "Lecturer ACCF Keetmanshoop").getByRole("link", { name: "Lecturer ACCF Keetmanshoop" }).click();
  await expect(record(page).getByRole("heading", { name: "Classes" })).toBeVisible();
  await expect(record(page).getByText("ACC1511")).toBeVisible();
  await page.getByRole("link", { name: "Academic staff" }).first().click();
  await page.getByRole("tab", { name: /^Incomplete/ }).click();
  await tableRow(page, "Lecturer MGMT Windhoek").getByRole("link", { name: "Lecturer MGMT Windhoek" }).click();
  await expect(page.getByRole("button", { name: "Link staff record" })).toBeVisible();
});

test("the head of department sees each lecturer's workload in a semester; the Registrar sets the rule", async ({ page }) => {
  await signIn(page, "head-of-department.accf");
  await page.goto("/academic-staff?tab=workload&year=2026&semester=Semester%202");
  await expect(page.getByRole("button", { name: "Semester 2" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("6 to 16 h a week")).toBeVisible();
  await expect(page.getByRole("button", { name: "Change" })).toHaveCount(0); // the Registrar's
  // one module of four hours a week, and a three-hour paper invigilated
  await expect(tableRow(page, "Lecturer ACCF Keetmanshoop")).toContainText(/4 h.*3 h.*Light/);
  await expect(tableRow(page, "Lecturer ACCF Windhoek and Oshakati")).toContainText("Not allocated");
  await expect(tableRow(page, "Lecturer COMP Windhoek")).toHaveCount(0); // another faculty
  await page.screenshot({ path: "e2e/results/workload.png", fullPage: true });

  await tableRow(page, "Lecturer ACCF Keetmanshoop").getByRole("link", { name: "Lecturer ACCF Keetmanshoop" }).click();
  await expect(record(page).getByRole("heading", { name: "Workload" })).toBeVisible();
  await expect(record(page).getByText("Hours a week").first()).toBeVisible();
  await page.screenshot({ path: "e2e/results/lecturer-workload.png", fullPage: true });
});

test("the Registrar changes the workload rule", async ({ page }) => {
  await signIn(page, "registrar");
  await page.goto("/academic-staff?tab=workload&year=2026&semester=Semester%201");
  await page.getByRole("button", { name: "Change" }).click();
  await expect(page.getByLabel("At least")).toHaveValue("6 h");
  await expect(page.getByLabel("At most")).toHaveValue("16 h");
  await page.getByRole("button", { name: "Cancel" }).click();
});
