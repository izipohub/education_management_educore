/** Dates as the university reads them: DD-MM-YYYY (AGENT.md 9) */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const [date] = value.split(" ");
  const [year, month, day] = (date ?? "").split("-");
  return year && month && day ? `${day}-${month}-${year}` : value;
}

/** "2027-02-01" → a local Date at midnight (not UTC, which would shift the day in some time zones) */
export function fromIsoDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year ?? 1970, (month ?? 1) - 1, day ?? 1);
}

/** a Date → "2027-02-01", from its local calendar day */
export function toIsoDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

const NUMBER = new Intl.NumberFormat("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Namibian dollars: "N$ 33,400.00" (AGENT.md 9) */
export function formatMoney(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : `N$ ${NUMBER.format(value)}`;
}

/** "registry-officer.osh@educore.localhost" → "registry-officer.osh" */
export function shortUser(user: string | null | undefined): string {
  return user ? user.replace(/@.*$/, "") : "";
}
