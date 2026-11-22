import { get, post } from "@/core/api/client";

export const STATUSES = ["Applied", "Approved", "Rejected", "Admitted"] as const;
export type Status = (typeof STATUSES)[number];
export type Action = "Approve" | "Reject" | "Withdraw Offer" | "Reconsider";

/** Actions that need a written reason (the server checks this too) */
export const NEEDS_REASON: Action[] = ["Reject", "Withdraw Offer"];

export interface Application {
  name: string;
  applicant: string;
  offering: string;
  program: string;
  campus: string;
  mode_of_study: string;
  academic_year: string;
  application_date: string | null;
  status: Status;
  decided_by: string | null;
  decided_on: string | null;
  decision_reason: string | null;
  /** what this user may do now, from the admission workflow */
  actions: Action[];
}

export interface Places {
  capacity: number | null;
  taken: number;
}

export interface ApplicationsPage {
  rows: Application[];
  counts: Record<Status, number>;
  /** the year shown: the one asked for, else the newest with applications */
  academic_year: string | null;
  academic_years: string[];
  /** keyed "<offering>|<academic year>" */
  capacity: Record<string, Places>;
}

export function listApplications(params: { status: Status; academic_year?: string; search?: string }) {
  return get<ApplicationsPage>("educore.api.v1.admissions.applications", params);
}

export function decide(name: string, action: Action, reason?: string) {
  return post<Application>("educore.api.v1.admissions.decide", { name, action, reason });
}
