import { get, http, post, toApiError } from "@/core/api/client";

/** Disciplinary cases (educore.api.v1.discipline): reported by staff, handled by Student Affairs, appeals decided by the
 * Registrar, followed by the student from the hearing on */
const API = "educore.api.v1.discipline";

export const DISCIPLINE_ROLES = ["Student Affairs Officer", "Registrar", "System Manager"];

export type CaseStatus = "Reported" | "Investigating" | "Hearing" | "Decided" | "Appealed" | "Closed" | "Dismissed";
export type Sanction = "Warning" | "Written warning" | "Fine" | "Suspension" | "Expulsion";
export const SANCTIONS: Sanction[] = ["Warning", "Written warning", "Fine", "Suspension", "Expulsion"];
/** what Student Affairs decides itself in a minor case; the rest is the committee's after a hearing */
export const MINOR_SANCTIONS: Sanction[] = ["Warning", "Written warning", "Fine"];

export interface CaseRow {
  name: string;
  student: string;
  student_name: string;
  campus: string | null;
  status: CaseStatus;
  level: "Minor" | "Serious" | null;
  incident_date: string | null;
  reported_on: string | null;
  hearing_on: string | null;
  sanction: Sanction | null;
  appealed_on: string | null;
}

/** what the student sees */
export interface MyCase {
  name: string;
  status: CaseStatus;
  level: string | null;
  charge: string | null;
  hearing_on: string | null;
  hearing_venue: string | null;
  finding: "Responsible" | "Not responsible" | null;
  sanction: Sanction | null;
  /** the outcome in words */
  outcome: string | null;
  decision_note: string | null;
  decided_on: string | null;
  appeal_until: string | null;
  appeal_reason: string | null;
  appealed_on: string | null;
  appeal_outcome: "Upheld" | "Changed" | "Overturned" | null;
  appeal_note: string | null;
  fine: number;
  fine_unpaid: boolean;
  suspended_from: string | null;
  suspended_until: string | null;
  can_appeal?: boolean;
}

export interface DisciplinaryCase extends MyCase {
  student: string;
  student_name: string;
  campus: string | null;
  reported_by: string | null;
  reported_on: string | null;
  incident_date: string | null;
  incident: string;
  evidence: boolean;
  investigated_by: string | null;
  investigation_note: string | null;
  committee: string | null;
  hearing_note: string | null;
  decided_by: string | null;
  appeal_decided_by: string | null;
  /** earlier cases in which the student was found responsible */
  earlier: number;
  can_handle: boolean;
  can_decide_appeal: boolean;
}

export async function reportMisconduct(student: string, incidentDate: string, incident: string, file: File | null) {
  const form = new FormData();
  form.append("student", student);
  form.append("incident_date", incidentDate);
  form.append("incident", incident);
  if (file) form.append("file", file);
  try {
    return (await http.post<{ message: { name: string; student_name: string } }>(`/api/method/${API}.report`, form)).data.message;
  } catch (error) {
    throw toApiError(error);
  }
}

export const listCases = () => get<{ rows: CaseRow[]; appeal_days: number; can_set_rules: boolean; can_handle: boolean }>(`${API}.cases`);
export const getCase = (name: string) => get<DisciplinaryCase>(`${API}.case`, { name });
export const investigateCase = (name: string) => post<DisciplinaryCase>(`${API}.investigate`, { name });
export const dismissCase = (name: string, note: string) => post<DisciplinaryCase>(`${API}.dismiss`, { name, note });
export const scheduleHearing = (name: string, data: { charge: string; hearing_on: string; venue: string; committee?: string; note?: string }) =>
  post<DisciplinaryCase>(`${API}.schedule_hearing`, { name, ...data });
export interface DecisionInput {
  finding: string;
  reasons: string;
  sanction?: string | null;
  fine?: number;
  suspended_from?: string | null;
  suspended_until?: string | null;
  hearing_note?: string;
}
export const decideCase = (name: string, data: DecisionInput) => post<DisciplinaryCase>(`${API}.decide`, { name, ...data });
export const decideAppeal = (name: string, data: { outcome: string; note: string; sanction?: string | null; fine?: number; suspended_from?: string | null; suspended_until?: string | null }) =>
  post<DisciplinaryCase>(`${API}.decide_appeal`, { name, ...data });
export const saveDisciplineRules = (appealDays: number) => post<{ appeal_days: number }>(`${API}.save_rules`, { appeal_days: appealDays });
export const evidenceUrl = (name: string) => `/api/method/${API}.evidence?name=${encodeURIComponent(name)}`;

// the student
export const myCases = () => get<MyCase[]>(`${API}.mine`);
export const appealCase = (name: string, reason: string) => post<MyCase[]>(`${API}.appeal`, { name, reason });
