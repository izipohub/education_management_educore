import { get, post } from "@/core/api/client";

/** who places and lifts holds (educore.api.v1.clearance.CLEARANCE_ROLES) */
export const CLEARANCE_ROLES = ["Bursar", "Finance Officer", "Student Fees Officer", "System Manager"];

export interface ClearanceRow {
  name: string;
  student_name: string;
  campus: string | null;
  owing: number;
  holds: number;
  cleared: boolean;
}

export interface Hold {
  name: string;
  reason: string;
  status?: "Active" | "Lifted";
  placed_by: string;
  placed_on: string;
  lifted_by?: string | null;
  lifted_on?: string | null;
  lift_note?: string | null;
}

export interface StudentClearance {
  name: string;
  student_name: string;
  campus: string | null;
  student_email_id: string | null;
  cleared: boolean;
  owing: number;
  holds: Hold[];
  reasons: string[];
  invoices: { name: string; posting_date: string; due_date: string; grand_total: number; outstanding_amount: number; remarks: string | null; is_return: 0 | 1 }[];
  history: Hold[];
  sponsors: { sponsor_name: string; academic_year: string; amount: number; status: string }[];
}

const API = "educore.api.v1.clearance";
export const listClearance = () => get<{ rows: ClearanceRow[]; max_owing: number }>(`${API}.students`);
export const getClearance = (name: string) => get<StudentClearance>(`${API}.student`, { name });
export const placeHold = (student: string, reason: string) => post<StudentClearance>(`${API}.place_hold`, { student_id: student, reason });
export const liftHold = (hold: string, note: string) => post<StudentClearance>(`${API}.lift_hold`, { hold, note });
