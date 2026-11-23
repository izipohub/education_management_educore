import { useSession } from "@/core/auth/session";

/**
 * Registration has two groups, as Namibian universities run it: first-year students (admitted applicants the
 * registry makes students: record, number, login, the year's fees) and senior students (returning students who
 * register their courses each year, approved by the faculty). Each officer sees their own group; the Registrar
 * sees both.
 */
export type Group = "first-year" | "senior";

export const GROUPS: { value: Group; label: string; roles: string[] }[] = [
  { value: "first-year", label: "First-year students", roles: ["Registry Officer", "Registrar"] },
  { value: "senior", label: "Senior students", roles: ["Faculty Officer", "Registrar"] },
];

export const REGISTRATION_ROLES = [...new Set(GROUPS.flatMap((g) => g.roles))];

export function allowedGroups() {
  const session = useSession();
  return GROUPS.filter((g) => session.hasRole(...g.roles));
}

/** the group asked for, if this user has it; else their first */
export function pickGroup(asked: unknown): Group {
  const allowed = allowedGroups();
  return allowed.find((g) => g.value === asked)?.value ?? allowed[0]?.value ?? "first-year";
}
