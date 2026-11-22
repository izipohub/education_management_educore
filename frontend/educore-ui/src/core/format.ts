/** Dates as the university reads them: DD-MM-YYYY (AGENT.md 9) */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const [date] = value.split(" ");
  const [year, month, day] = (date ?? "").split("-");
  return year && month && day ? `${day}-${month}-${year}` : value;
}

/** "registry-officer.osh@educore.localhost" → "registry-officer.osh" */
export function shortUser(user: string | null | undefined): string {
  return user ? user.replace(/@.*$/, "") : "";
}
