import { get, post } from "@/core/api/client";

/** Education's statuses; "Leave" reads Excused */
export type AttendanceStatus = "Present" | "Absent" | "Leave";
export const STATUS_LABELS: Record<AttendanceStatus, string> = { Present: "Present", Absent: "Absent", Leave: "Excused" };

export interface AttendanceSummary {
  /** the university's minimum attendance, percent; 0: none */
  minimum: number;
  /** each lesson held (or each day's register without a timetable) */
  sessions: { date: string; start_time: string | null; present: number; absent: number; excused: number }[];
  students: { student: string; student_name: string; present: number; absent: number; excused: number; rate: number | null; below: boolean }[];
}

export interface Lesson {
  key: string;
  start_time: string;
  end_time: string;
  room_name: string;
  kind: string;
  taken: boolean;
}

export interface Register extends AttendanceSummary {
  class: { name: string; course: string; course_name: string; code: string | null; campus: string | null; academic_year: string };
  date: string;
  /** the module's lessons that day (from the timetable) and the one shown */
  lessons: Lesson[];
  lesson: string | null;
  /** the weekdays the module meets this semester; another day has no register */
  lesson_days: string[];
  /** the module has a timetable: its registers are per lesson */
  timetabled: boolean;
  taken: boolean;
  entries: { student: string; student_name: string; status: AttendanceStatus | null }[];
}

const API = "educore.api.v1.attendance";
export const getRegister = (group: string, date?: string, lesson?: string | null) =>
  get<Register>(`${API}.register`, { group, ...(date ? { date } : {}), ...(lesson ? { lesson } : {}) });
export const takeRegister = (group: string, date: string, entries: { student: string; status: AttendanceStatus }[], lesson?: string | null) =>
  post<Register>(`${API}.take`, { group, date, entries, ...(lesson ? { lesson } : {}) });
