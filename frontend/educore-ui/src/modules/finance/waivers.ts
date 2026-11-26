import { get, post } from "@/core/api/client";

/** who requests fee waivers (educore.api.v1.waivers.WAIVER_ROLES); the Bursar decides */
export const WAIVER_ROLES = ["Bursar", "Finance Officer", "Student Fees Officer", "System Manager"];
export const WAIVE_KINDS = ["Percent of fees", "Amount", "Late registration fee"] as const;
export type WaiveKind = (typeof WAIVE_KINDS)[number];

export interface Waiver {
  name: string;
  student: string;
  student_name: string;
  campus: string | null;
  academic_year: string;
  waive: WaiveKind;
  value: number;
  reason: string;
  status: "Requested" | "Approved" | "Rejected" | "Withdrawn";
  amount: number;
  credit_note: string | null;
  requested_by: string;
  requested_by_name: string | null;
  requested_on: string | null;
  decided_by: string | null;
  decided_by_name: string | null;
  decided_on: string | null;
  decision_note: string | null;
  can_decide: boolean;
  /** the Bursar may take back an approved waiver */
  can_withdraw: boolean;
}

/** what is waived, in words: "25% of the fees", "N$ 1,000.00", "The late registration fee" */
export function waiverWhat(w: Pick<Waiver, "waive" | "value">, money: (n: number) => string): string {
  if (w.waive === "Percent of fees") return `${w.value}% of the fees`;
  if (w.waive === "Amount") return money(w.value);
  return "The late registration fee";
}

const API = "educore.api.v1.waivers";
export const listWaivers = () => get<{ rows: Waiver[]; can_decide: boolean }>(`${API}.waivers_list`);
export const requestWaiver = (body: { student_id: string; academic_year: string; waive: WaiveKind; value?: number; reason: string }) =>
  post<Waiver>(`${API}.request`, body);
export const approveWaiver = (name: string, note?: string) => post<Waiver>(`${API}.approve`, { name, note });
export const rejectWaiver = (name: string, note: string) => post<Waiver>(`${API}.reject`, { name, note });
export const withdrawWaiver = (name: string, note: string) => post<Waiver>(`${API}.withdraw`, { name, note });
