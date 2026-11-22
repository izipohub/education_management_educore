import { describe, expect, it } from "vitest";
import { formatDate, shortUser } from "@/core/format";

describe("formatDate", () => {
  it("shows dates as DD-MM-YYYY", () => {
    expect(formatDate("2026-09-15")).toBe("15-09-2026");
    expect(formatDate("2026-11-22 12:00:00.123")).toBe("22-11-2026");
  });

  it("leaves empty and unexpected values alone", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate("soon")).toBe("soon");
  });
});

describe("shortUser", () => {
  it("drops the email domain", () => {
    expect(shortUser("registry-officer.osh@educore.localhost")).toBe("registry-officer.osh");
    expect(shortUser(null)).toBe("");
  });
});
