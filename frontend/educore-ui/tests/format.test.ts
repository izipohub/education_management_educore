import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, fromIsoDate, shortUser, toIsoDate } from "@/core/format";

describe("ISO dates", () => {
  it("round-trips a calendar day without shifting it", () => {
    expect(toIsoDate(fromIsoDate("2027-02-01"))).toBe("2027-02-01");
    expect(fromIsoDate("2027-02-01").getDate()).toBe(1);
  });
});

describe("formatMoney", () => {
  it("shows Namibian dollars with two decimals", () => {
    expect(formatMoney(33400)).toBe("N$ 33,400.00");
    expect(formatMoney(0)).toBe("N$ 0.00");
    expect(formatMoney(null)).toBe("");
  });
});

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
