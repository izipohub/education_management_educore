import { get, post } from "@/core/api/client";

/** Education's statuses; "Leave" reads Excused */
export type AttendanceStatus = "Present" | "Absent" | "Leave";
export const STATUS_LABELS: Record<AttendanceStatus, string> = { Present: "Present", Absent: "Absent", Leave: "Excused" };

export interface AttendanceSummary {
  /** the university's minimum attendance, percent; 0: none */
  minimum: number;
  sessions: { date: string; present: number; absent: number; excused: number }[];
  students: { student: string; student_name: string; present: number; absent: number; excused: number; rate: number | null; below: boolean }[];
}

export interface Register extends AttendanceSummary {
  class: { name: string; course: string; course_name: string; code: string | null; campus: string | null; academic_year: string };
  date: string;
  taken: boolean;
  entries: { student: string; student_name: string; status: AttendanceStatus | null }[];
}

const API = "educore.api.v1.attendance";
export const getRegister = (group: string, date?: string) => get<Register>(`${API}.register`, { group, ...(date ? { date } : {}) });
export const takeRegister = (group: string, date: string, entries: { student: string; status: AttendanceStatus }[]) =>
  post<Register>(`${API}.take`, { group, date, entries });
